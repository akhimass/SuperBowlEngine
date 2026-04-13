from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from .cfb_client import cfbd_api_key
from .cfb_stats import build_cfbd_scores_for_combine_class
from .consensus import aggregate_market_consensus, build_simulation_board_order, compute_reach_risk
from .draft_board import final_draft_score
from .loaders import load_combine, load_draft_picks
from .player_model import (
    age_adjustment_score,
    build_prospect_score,
    combine_movement_efficiency_score,
    compute_athletic_score_row,
    nfl_production_efficiency_scores,
    _parse_height_inches,
)
from .positions import bucket_for_combine_pos
from .scheme_fit import compute_scheme_fit
from .team_context import TeamContext, build_team_context, team_context_summary
from .team_needs import NEED_BUCKETS


def _slug_id(*parts: Any) -> str:
    raw = "|".join(str(p) for p in parts if p is not None and str(p) != "nan")
    s = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return s or "unknown"


def _player_id_from_row(row: pd.Series) -> str:
    pid = row.get("pfr_id")
    if pid is not None and str(pid).strip() and str(pid) != "nan":
        return str(pid).strip()
    return _slug_id(row.get("player_name"), row.get("pos"), row.get("school"))


def _prepare_prospect_frame(
    combine_season: int,
    cfb_season: Optional[int] = None,
) -> tuple[pd.DataFrame, Dict[str, Any], Dict[str, Dict[str, Any]]]:
    c = load_combine([combine_season])
    dp = load_draft_picks([combine_season])
    if not dp.empty and "pfr_player_id" in dp.columns:
        dp = dp.sort_values(["games", "car_av"], ascending=False, na_position="last")
        dp = dp.drop_duplicates(subset=["pfr_player_id"], keep="first")
        merged = c.merge(
            dp,
            left_on="pfr_id",
            right_on="pfr_player_id",
            how="left",
            suffixes=("", "_dp"),
        )
    else:
        merged = c.copy()

    merged["pos_bucket"] = merged["pos"].map(lambda x: bucket_for_combine_pos(str(x)))
    merged["player_id"] = merged.apply(_player_id_from_row, axis=1)
    merged["height_in"] = merged["ht"].map(_parse_height_inches)
    merged["weight_lb"] = pd.to_numeric(merged["wt"], errors="coerce")

    cfb_year = int(cfb_season) if cfb_season is not None else int(combine_season) - 1
    cfb_scores: Dict[str, Dict[str, Any]] = {}
    cfb_meta: Dict[str, Any] = {
        "cfb_enabled": False,
        "cfb_season": cfb_year,
        "hint": "Set CFBD_API_KEY (CollegeFootballData.com) for college production/efficiency.",
    }
    k = cfbd_api_key()
    if k:
        try:
            cfb_scores, cfb_meta = build_cfbd_scores_for_combine_class(merged, cfb_year, k)
            cfb_meta["cfb_enabled"] = True
            cfb_meta["cfb_season"] = cfb_year
        except Exception as e:  # noqa: BLE001
            cfb_scores = {}
            cfb_meta = {
                "cfb_enabled": True,
                "cfb_error": str(e),
                "cfb_season": cfb_year,
            }

    # Athletic scores within combine position group
    athletic_vals: Dict[int, float] = {}
    for _, g in merged.groupby("pos"):
        for idx in g.index:
            athletic_vals[idx] = compute_athletic_score_row(merged.loc[idx], g)
    merged["athletic_score"] = merged.index.map(lambda i: athletic_vals.get(i, 50.0))

    merged["weight_percentile_proxy"] = (
        merged.groupby("pos_bucket")["weight_lb"]
        .rank(pct=True, method="average")
        .mul(100.0)
        .fillna(50.0)
    )

    prod_scores: Dict[int, float] = {}
    eff_scores: Dict[int, float] = {}
    sources: Dict[int, str] = {}
    age_scores: Dict[int, float] = {}

    for pos, g in merged.groupby("pos"):
        for idx in g.index:
            row = merged.loc[idx]
            pid = str(row.get("player_id") or "")
            cfb = cfb_scores.get(pid) if pid else None
            has_cfb = bool(cfb)
            has_dp = pd.notna(row.get("pfr_player_id")) and str(row.get("pfr_player_id", "")).strip()
            games = float(row.get("games") or 0) if has_dp else 0.0
            if has_dp and games > 0:
                nfl_p, nfl_e, nfl_src = nfl_production_efficiency_scores(row)
                if has_cfb:
                    p = 0.35 * float(cfb["cfb_production_score"]) + 0.65 * nfl_p
                    e = 0.35 * float(cfb["cfb_efficiency_score"]) + 0.65 * nfl_e
                    src = "cfbd_player_season_stats_plus_nflverse_career"
                else:
                    p, e, src = nfl_p, nfl_e, nfl_src
            elif has_cfb:
                p = float(cfb["cfb_production_score"])
                e = float(cfb["cfb_efficiency_score"])
                src = "cfbd_player_season_stats"
            elif has_dp:
                p = 50.0
                e = combine_movement_efficiency_score(row, g)
                src = "nflverse_pre_rookie_combine_cod"
            else:
                p = 50.0
                e = combine_movement_efficiency_score(row, g)
                src = "combine_only_pending_nfl_career_stats"
            prod_scores[idx] = p
            eff_scores[idx] = e
            sources[idx] = src
            age_raw = row.get("age")
            try:
                age_f = float(age_raw) if pd.notna(age_raw) else float("nan")
            except (TypeError, ValueError):
                age_f = float("nan")
            age_scores[idx] = age_adjustment_score(age_f if not np.isnan(age_f) else None, combine_season)

    merged["production_score"] = merged.index.map(prod_scores.get)
    merged["efficiency_score"] = merged.index.map(eff_scores.get)
    merged["production_source"] = merged.index.map(sources.get)
    merged["age_adjustment"] = merged.index.map(age_scores.get)

    prospect_scores: Dict[int, float] = {}
    for idx, row in merged.iterrows():
        pdata = {
            "athletic_score": float(row["athletic_score"]),
            "production_score": float(row["production_score"]),
            "efficiency_score": float(row["efficiency_score"]),
            "age_adjustment": float(row["age_adjustment"]),
            "pos_bucket": str(row["pos_bucket"]),
            "production_source": str(row["production_source"]),
            "weight_percentile_proxy": float(row.get("weight_percentile_proxy", 50.0)),
        }
        pid = str(row.get("player_id") or "")
        if pid and pid in cfb_scores:
            for k, v in cfb_scores[pid].items():
                if k.startswith("cfb_") or k == "production_source_detail":
                    pdata[k] = v
        prospect_scores[idx] = float(build_prospect_score(pdata)["prospect_score"])

    merged["prospect_score"] = merged.index.map(prospect_scores.get)
    return merged, cfb_meta, cfb_scores


def build_draft_board(
    team: str,
    combine_season: int,
    eval_season: int,
    *,
    cfb_season: Optional[int] = None,
    consensus_extra_directories: Optional[Sequence[str]] = None,
    draft_pick_positions: Optional[Sequence[int]] = None,
    team_context: Optional[TeamContext] = None,
) -> Dict[str, Any]:
    """
    Full board: prospects with scores, team needs, scheme profile, consensus ordering.
    ``team`` and ``eval_season`` are required; optional ``team_context`` avoids duplicate
    nflverse loads when callers already built runtime context.
    """
    team = str(team).upper()
    prospects, cfb_meta, cfb_scores = _prepare_prospect_frame(combine_season, cfb_season=cfb_season)
    if team_context is not None:
        if team_context.team != team or int(team_context.season) != int(eval_season):
            raise ValueError("team_context team/season must match team and eval_season arguments")
        ctx = team_context
    else:
        ctx = build_team_context(
            team,
            int(eval_season),
            draft_pick_positions=list(draft_pick_positions) if draft_pick_positions else [],
        )

    needs = ctx.needs_detail
    scheme = ctx.scheme_profile
    need_map = ctx.needs
    board_buckets = prospects["pos_bucket"].astype(str).tolist()
    scores_by_position: Dict[str, List[float]] = (
        prospects.groupby("pos_bucket")["prospect_score"].apply(lambda s: s.astype(float).tolist()).to_dict()
    )

    rows: List[Dict[str, Any]] = []
    for _, row in prospects.iterrows():
        pos_b = str(row["pos_bucket"])
        need_score = float(need_map.get(pos_b, need_map.get("LB", 35.0)))
        if pos_b not in NEED_BUCKETS:
            need_score = float(np.mean(list(need_map.values())))

        player_profile = {
            "pos": str(row.get("pos", "")),
            "pos_bucket": pos_b,
            "height_in": float(row["height_in"]) if pd.notna(row["height_in"]) else float("nan"),
            "weight_lb": float(row["weight_lb"]) if pd.notna(row["weight_lb"]) else float("nan"),
            "forty": float(row["forty"]) if pd.notna(row.get("forty")) else None,
            "vertical": float(row["vertical"]) if pd.notna(row.get("vertical")) else None,
        }
        fit = compute_scheme_fit(player_profile, team_context=ctx)
        fus = final_draft_score(
            float(row["prospect_score"]),
            need_score,
            float(fit["scheme_fit_score"]),
            pos_b,
            board_buckets,
            scores_by_position=scores_by_position,
        )

        radar = {
            "athleticism": float(row["athletic_score"]),
            "production": float(row["production_score"]),
            "efficiency": float(row["efficiency_score"]),
            "scheme_fit": float(fit["scheme_fit_score"]),
            "team_need": need_score,
        }

        pid = str(row["player_id"])
        cfb_row = cfb_scores.get(pid)
        rows.append(
            {
                "player_id": pid,
                "player_name": str(row.get("player_name", "")),
                "pos": str(row.get("pos", "")),
                "pos_bucket": pos_b,
                "school": str(row.get("school", "")),
                "cfb_id": row.get("cfb_id"),
                "pfr_id": row.get("pfr_id"),
                "combine_season": int(combine_season),
                "height": row.get("ht"),
                "weight_lb": float(row["weight_lb"]) if pd.notna(row.get("wt")) else None,
                "forty": float(row["forty"]) if pd.notna(row.get("forty")) else None,
                "vertical": float(row["vertical"]) if pd.notna(row.get("vertical")) else None,
                "bench": float(row["bench"]) if pd.notna(row.get("bench")) else None,
                "broad_jump": float(row["broad_jump"]) if pd.notna(row.get("broad_jump")) else None,
                "cone": float(row["cone"]) if pd.notna(row.get("cone")) else None,
                "shuttle": float(row["shuttle"]) if pd.notna(row.get("shuttle")) else None,
                "prospect_score": float(row["prospect_score"]),
                "team_need_score": round(need_score, 2),
                "scheme_fit_score": float(fit["scheme_fit_score"]),
                "final_draft_score": float(fus["final_draft_score"]),
                "score_breakdown": {
                    "prospect": {
                        "prospect_score": float(row["prospect_score"]),
                        "athletic_score": float(row["athletic_score"]),
                        "production_score": float(row["production_score"]),
                        "efficiency_score": float(row["efficiency_score"]),
                        "age_adjustment": float(row["age_adjustment"]),
                        "production_source": str(row["production_source"]),
                    },
                    "fusion": fus,
                    "scheme_fit_detail": fit,
                    "cfb": cfb_row,
                },
                "radar": radar,
            }
        )

    model_sorted = sorted(rows, key=lambda r: (-r["prospect_score"], r["player_name"]))
    model_rank_map = {r["player_id"]: i + 1 for i, r in enumerate(model_sorted)}

    extra_dirs = list(consensus_extra_directories) if consensus_extra_directories else None
    market, cons_meta = aggregate_market_consensus(rows, extra_directories=extra_dirs)

    for r in rows:
        pid = r["player_id"]
        r["model_rank"] = model_rank_map[pid]
        m = market.get(pid, {})
        r["consensus_rank"] = m.get("consensus_rank")
        r["avg_pick_position"] = m.get("avg_pick_position")
        r["consensus_rank_variance"] = m.get("rank_variance")
        r["market_value_score"] = m.get("market_value_score")
        r["reach_risk"] = compute_reach_risk(r["model_rank"], m.get("consensus_rank"))
        r["consensus_boards_matched"] = m.get("board_count")

    sim_order = build_simulation_board_order(rows, market)
    rows.sort(key=lambda r: (-r["prospect_score"], r["player_name"]))

    sources = [
        "nflreadpy.load_combine",
        "nflreadpy.load_draft_picks",
        "nflreadpy.load_pbp",
        "nflreadpy.load_snap_counts",
        "nflreadpy.load_injuries",
        "nflreadpy.load_player_stats",
    ]
    if cfb_meta.get("cfb_enabled") and not cfb_meta.get("cfb_error"):
        sources.append("api.collegefootballdata.com (CFBD player season stats)")

    return {
        "team": team,
        "combine_season": combine_season,
        "eval_season": eval_season,
        "cfb_season": cfb_meta.get("cfb_season", int(combine_season) - 1),
        "team_needs": needs,
        "team_scheme": scheme,
        "team_context_summary": team_context_summary(ctx),
        "consensus_board": sim_order,
        "prospects": rows,
        "meta": {
            "n_prospects": len(rows),
            "data_sources": sources,
            "cfb": cfb_meta,
            "consensus": cons_meta,
            "simulation_board_note": (
                "Order blends external board files (when configured) with model grades; "
                "set GRIDIRONIQ_DRAFT_CONSENSUS_DIR for market-aware simulations."
            ),
        },
    }


def run_availability_and_recommendations(
    board: Dict[str, Any],
    pick_number: int,
    *,
    n_simulations: int = 800,
    temperature: float = 2.0,
    available_ids: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    from .decision_engine import four_ranking_modes, recommend_pick
    from .simulator import simulate_draft

    order = [str(i) for i in range(1, pick_number + 8)]  # length anchor; only count matters
    consensus = board["consensus_board"]
    sim = simulate_draft(
        order,
        consensus,
        pick_number,
        n_simulations=n_simulations,
        temperature=temperature,
    )
    avail = sim["availability"]
    prospects = board["prospects"]
    if available_ids is None:
        pool = prospects
    else:
        want = {str(x) for x in available_ids}
        pool = [p for p in prospects if p["player_id"] in want]

    rec_input = [dict(p) for p in pool]
    ranked = recommend_pick(board["team"], pick_number, rec_input, avail)
    four = four_ranking_modes(pool)
    return {"simulation": sim, "recommendations": ranked, "four_ranking_modes": four}


def _cli_main() -> None:
    import argparse
    import json
    from pathlib import Path

    p = argparse.ArgumentParser(description="GridironIQ draft board (nflverse-backed).")
    p.add_argument("--team", required=True, help="NFL team abbreviation, e.g. KC")
    p.add_argument("--season", type=int, required=True, help="NFL eval season (e.g. 2025 for 2025 PBP/stats)")
    p.add_argument(
        "--combine-season",
        type=int,
        default=None,
        help="Combine class year (defaults to season + 1)",
    )
    p.add_argument("--picks", type=int, nargs="*", default=[], help="Team-owned draft slot numbers (metadata only)")
    p.add_argument("--top-n", type=int, default=10, dest="top_n", help="How many prospects to print")
    p.add_argument("--report", action="store_true", help="Generate draft room PDF report(s)")
    p.add_argument(
        "--report-type",
        choices=("needs", "prospect", "board", "all"),
        default="all",
        help="Which PDF(s) to generate when --report is set",
    )
    p.add_argument(
        "--report-output-dir",
        type=str,
        default="outputs/reports/draft/",
        help="Directory for PDF output (default under outputs/reports for /report-assets)",
    )
    p.add_argument("--no-ai", action="store_true", help="Use template fallback text (no local Phi-4 calls)")
    p.add_argument(
        "--prospect",
        type=str,
        default="",
        help="Player name substring for --report-type prospect",
    )
    p.add_argument("--n-simulations", type=int, default=800, dest="n_simulations", help="Monte Carlo runs per pick")
    p.add_argument("--temperature", type=float, default=2.0, help="Simulation board temperature")
    args = p.parse_args()
    combine_season = int(args.combine_season) if args.combine_season is not None else int(args.season) + 1
    board = build_draft_board(
        str(args.team).upper(),
        combine_season,
        int(args.season),
        draft_pick_positions=list(args.picks),
    )
    ranked = sorted(board["prospects"], key=lambda r: (-float(r["final_draft_score"]), r["player_name"]))[: int(args.top_n)]
    slim = [
        {
            "player_id": r["player_id"],
            "player_name": r["player_name"],
            "pos": r["pos"],
            "final_draft_score": r["final_draft_score"],
            "prospect_score": r["prospect_score"],
            "team_need_score": r["team_need_score"],
        }
        for r in ranked
    ]
    print(
        json.dumps(
            {"team_context_summary": board["team_context_summary"], "top_prospects": slim},
            indent=2,
        )
    )

    if args.report:
        from gridironiq.reports.ai_content import get_content_generator
        from gridironiq.reports.models import from_pipeline_output, prospect_dict_to_card
        from gridironiq.reports.renderer import ReportRenderError, ReportRenderer

        summary = board.get("team_context_summary") or {}
        pick_slots = list(summary.get("draft_pick_positions") or [])
        sim_picks = list(args.picks) if args.picks else (pick_slots or [1])
        rec_by_pick: Dict[int, List[Dict[str, Any]]] = {}
        for pick in sim_picks:
            pack = run_availability_and_recommendations(
                board,
                int(pick),
                n_simulations=int(args.n_simulations),
                temperature=float(args.temperature),
            )
            rec_by_pick[int(pick)] = pack["recommendations"]

        extended: Dict[str, Any] = dict(board)
        extended["recommendations_by_pick"] = rec_by_pick
        report = from_pipeline_output(
            extended,
            str(args.team).upper(),
            int(args.season),
            pick_slots=list(args.picks) if args.picks else None,
            top_n=int(args.top_n),
        )

        gen = get_content_generator(use_ai=not bool(args.no_ai))
        renderer = ReportRenderer()
        out_dir = Path(args.report_output_dir)

        def _print_path(path: Path) -> None:
            print(f"Report generated: {path.resolve()}")

        rt = str(args.report_type)
        try:
            if rt == "needs":
                _print_path(renderer.render_team_need_report(report, gen, out_dir))
            elif rt == "board":
                _print_path(
                    renderer.render_full_draft_board(
                        report,
                        gen,
                        out_dir,
                        top_n_prospects=int(args.top_n),
                    )
                )
            elif rt == "prospect":
                q = str(args.prospect or "").strip().lower()
                if not q:
                    raise SystemExit("--prospect NAME is required when --report-type prospect")
                match_pc = None
                for c in report.top_prospects:
                    if q in c.name.lower():
                        match_pc = c
                        break
                if match_pc is None:
                    for row in board["prospects"]:
                        if q in str(row.get("player_name", "")).lower():
                            match_pc = prospect_dict_to_card(row)
                            break
                if match_pc is None:
                    raise SystemExit(f"No prospect matching {args.prospect!r} on the board.")
                _print_path(renderer.render_prospect_card(match_pc, report.team_snapshot, gen, out_dir))
            else:
                for _, path in renderer.render_all(
                    report, gen, out_dir, top_n_prospects=int(args.top_n)
                ).items():
                    _print_path(path)
        except ImportError as e:
            raise SystemExit(
                "Draft PDF requires WeasyPrint and OS libraries (Pango, GObject). "
                "See https://doc.courtbouillon.org/weasyprint/stable/first_steps.html — "
                f"detail: {e}"
            ) from e
        except ReportRenderError as e:
            raise SystemExit(f"Report PDF failed: {e}") from e


if __name__ == "__main__":
    _cli_main()
