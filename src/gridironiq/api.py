from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .matchup_engine import MatchupResult, run_matchup
from .qb_production_engine import QBComparisonResult, compare_qbs
from .report_generator import generate_report
from .backtest_engine import BacktestResult, run_backtest
from .reports.matchup_report import build_matchup_report
from .reports.broadcast_report import build_broadcast_report
from .reports.presentation_report import build_presentation_report
from .schedule_engine import (
    Phase,
    build_game_report,
    list_schedule,
    run_schedule_predictions,
    run_schedule_reports,
)
from .assets import load_logo_manifest, get_team_logo
from .ai.schemas import ExplainerContext


class MatchupRequest(BaseModel):
    season: int
    team_a: str
    team_b: str
    mode: str = "opp_weighted"


class ReportMatchupRequest(BaseModel):
    season: int
    team_a: str
    team_b: str
    week: Optional[int] = None
    mode: str = "opp_weighted"
    generate_heatmaps: bool = False


class QBCompareRequest(BaseModel):
    season: int
    qb_a: str
    team_a: str
    qb_b: str
    team_b: str


class BacktestRequest(BaseModel):
    season: int


class AIExplainMatchupRequest(BaseModel):
    season: int
    team_a: str
    team_b: str
    mode: str = "opp_weighted"
    ai_mode: Optional[str] = None


class AIChatRequest(BaseModel):
    question: str
    context_type: str  # "matchup" | "historical_game" | "draft"
    season: int = 2024
    team_a: str = ""
    team_b: str = ""
    game_id: Optional[str] = None
    mode: str = "opp_weighted"
    ai_mode: Optional[str] = None
    draft_team: Optional[str] = None
    combine_season: Optional[int] = None
    eval_season: Optional[int] = None
    pick_number: Optional[int] = None
    cfb_season: Optional[int] = None
    consensus_dirs: Optional[list[str]] = None


def _normalize_consensus_dirs(items: Optional[list[str]]) -> Optional[list[str]]:
    if not items:
        return None
    out = [str(x).strip() for x in items if str(x).strip()]
    return out or None


class DraftSimulateRequest(BaseModel):
    team: str
    combine_season: int
    eval_season: int
    pick_number: int = 1
    n_simulations: int = 800
    temperature: float = 2.0
    cfb_season: Optional[int] = None
    consensus_dirs: Optional[list[str]] = None


class DraftRecommendRequest(BaseModel):
    team: str
    combine_season: int
    eval_season: int
    pick_number: int = 1
    n_simulations: int = 800
    temperature: float = 2.0
    available_player_ids: Optional[list[str]] = None
    cfb_season: Optional[int] = None
    consensus_dirs: Optional[list[str]] = None


class DraftAnalystRequest(BaseModel):
    team: str
    combine_season: int
    eval_season: int
    pick_number: int = 1
    n_simulations: int = 800
    temperature: float = 2.0
    ai_mode: Optional[str] = None
    cfb_season: Optional[int] = None
    consensus_dirs: Optional[list[str]] = None


class DraftTradeRequest(BaseModel):
    team: str
    combine_season: int
    eval_season: int
    current_pick: int
    max_target_pick: int = 40
    target_player_ids: Optional[list[str]] = None
    n_simulations: int = 400
    temperature: float = 2.0
    cfb_season: Optional[int] = None
    consensus_dirs: Optional[list[str]] = None


class DraftIntelligenceRequest(BaseModel):
    team: str
    combine_season: int
    eval_season: int
    pick_number: int
    n_simulations: int = 600
    temperature: float = 2.0
    trade_target_pick: Optional[int] = None
    cfb_season: Optional[int] = None
    consensus_dirs: Optional[list[str]] = None


class DraftReportRequest(BaseModel):
    team: str
    season: int
    picks: list[int] = []
    top_n: int = 10
    report_type: str = "all"
    use_ai: bool = False
    prospect_name: Optional[str] = None


app = FastAPI(title="GridironIQ Backend", version="0.1.0")

# Serve generated report images (heatmaps, charts) for frontend display.
# Only mounts the reports output folder.
app.mount("/report-assets", StaticFiles(directory="outputs/reports"), name="report-assets")

# Allow local frontend dev servers (Vite / Lovable) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/assets/team-logos")
def api_team_logos() -> Dict[str, Any]:
    """
    Return the team logo manifest (teams, unmatched, duplicates).
    Frontend can use this to resolve team abbreviation -> logo path.
    """
    return load_logo_manifest()


@app.get("/api/schedule")
def api_schedule(season: int, phase: str = "all") -> Dict[str, Any]:
    """
    Return schedule + prediction summary for a given season and phase.

    phase: "all" | "regular" | "postseason"
    """
    if phase not in {"all", "regular", "postseason"}:
        raise HTTPException(status_code=400, detail="phase must be one of: all, regular, postseason")
    try:
        games = list_schedule(season=season, phase=phase)  # type: ignore[arg-type]
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"season": season, "phase": phase, "games": games}


@app.get("/api/game-report")
def api_game_report(season: int, game_id: str) -> Dict[str, Any]:
    """
    Full report for a single historical game (schedule metadata + prediction + reports).
    """
    try:
        return build_game_report(season=season, game_id=game_id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/schedule/build")
def api_schedule_build(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Precompute schedule predictions (and optionally reports) for a season/phase.

    Body:
      { "season": 2024, "phase": "all", "build_reports": true }
    """
    season = int(payload.get("season", 0))
    phase_raw = str(payload.get("phase", "all"))
    build_reports = bool(payload.get("build_reports", False))

    if season <= 0:
        raise HTTPException(status_code=400, detail="season is required")
    if phase_raw not in {"all", "regular", "postseason"}:
        raise HTTPException(status_code=400, detail="phase must be one of: all, regular, postseason")

    phase_typed: Phase = phase_raw  # type: ignore[assignment]

    try:
        games = run_schedule_predictions(season=season, phase=phase_typed)
        report_index: Dict[str, Dict[str, Any]] = {}
        if build_reports:
            report_index = run_schedule_reports(season=season, phase=phase_typed)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "season": season,
        "phase": phase_raw,
        "games_processed": len(games),
        "reports_built": len(report_index),
    }


@app.post("/api/ai/explain-matchup")
def api_ai_explain_matchup(req: AIExplainMatchupRequest) -> Dict[str, Any]:
    """
    Run matchup + report pipeline and return only the AI Statistician object.
    """
    try:
        result: MatchupResult = run_matchup(
            season=req.season,
            team_a=req.team_a,
            team_b=req.team_b,
            mode=req.mode,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e

    report = generate_report(result)
    ai = report.get("ai_statistician") or {}
    return {"ai_statistician": ai}


@app.post("/api/ai/chat")
def api_ai_chat(req: AIChatRequest) -> Dict[str, Any]:
    """
    Game-/matchup-grounded AI chat. Answers ONLY using the current report context.
    """
    from .ai.chat import generate_ai_chat_answer
    from .ai.draft_analyst import build_draft_intel_payload
    from .ai.explainer import build_explainer_context
    from .draft.pipeline import build_draft_board, run_availability_and_recommendations
    from .reports.matchup_report import build_matchup_report
    from .reports.broadcast_report import build_broadcast_report

    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="question is required")

    ctx: ExplainerContext

    if req.context_type == "draft":
        if not req.draft_team or req.combine_season is None or req.eval_season is None:
            raise HTTPException(
                status_code=400,
                detail="draft context requires draft_team, combine_season, and eval_season",
            )
        pick_n = int(req.pick_number or 1)
        try:
            board = build_draft_board(
                req.draft_team,
                int(req.combine_season),
                int(req.eval_season),
                cfb_season=req.cfb_season,
                consensus_extra_directories=_normalize_consensus_dirs(req.consensus_dirs),
            )
            pack = run_availability_and_recommendations(
                board,
                pick_n,
                n_simulations=800,
                temperature=2.0,
            )
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(e)) from e
        intel = build_draft_intel_payload(board, pack["recommendations"], pack["simulation"])
        ctx = ExplainerContext(
            matchup={},
            scouting_report={},
            draft_intel=intel,
        )
        out = generate_ai_chat_answer(question=req.question, context=ctx, ai_mode=req.ai_mode)
        return out

    if not req.team_a or not req.team_b:
        raise HTTPException(status_code=400, detail="team_a and team_b are required for matchup chat")

    # Build the same grounded context we use for AI explanations.
    try:
        matchup = run_matchup(season=req.season, team_a=req.team_a, team_b=req.team_b, mode=req.mode)
        scouting = generate_report(matchup)
        situational = build_matchup_report(
            season=req.season,
            team_a=req.team_a,
            team_b=req.team_b,
            week=None,
            mode=req.mode,
            generate_heatmaps=False,
        )
        broadcast = build_broadcast_report(
            season=req.season,
            team_a=req.team_a,
            team_b=req.team_b,
            week=None,
            generate_heatmaps=False,
        )
        ctx = build_explainer_context(
            matchup,
            scouting,
            situational_report=situational,
            broadcast_report=broadcast,
            qb_report=None,
            visuals=None,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e

    out = generate_ai_chat_answer(question=req.question, context=ctx, ai_mode=req.ai_mode)
    return out


@app.get("/api/draft/board")
def api_draft_board(
    team: str,
    combine_season: int,
    eval_season: int,
    cfb_season: Optional[int] = None,
    consensus_dirs: Optional[str] = None,
) -> Dict[str, Any]:
    from .draft.pipeline import build_draft_board

    extra = (
        [p.strip() for p in consensus_dirs.split(",") if p.strip()] if consensus_dirs else None
    )
    try:
        return build_draft_board(
            team,
            combine_season,
            eval_season,
            cfb_season=cfb_season,
            consensus_extra_directories=extra,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/draft/simulate")
def api_draft_simulate(req: DraftSimulateRequest) -> Dict[str, Any]:
    from .draft.pipeline import build_draft_board, run_availability_and_recommendations

    try:
        board = build_draft_board(
            req.team,
            req.combine_season,
            req.eval_season,
            cfb_season=req.cfb_season,
            consensus_extra_directories=_normalize_consensus_dirs(req.consensus_dirs),
        )
        return run_availability_and_recommendations(
            board,
            int(req.pick_number),
            n_simulations=min(5000, max(50, int(req.n_simulations))),
            temperature=float(req.temperature),
            available_ids=None,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/draft/recommend")
def api_draft_recommend(req: DraftRecommendRequest) -> Dict[str, Any]:
    from .draft.pipeline import build_draft_board, run_availability_and_recommendations

    try:
        board = build_draft_board(
            req.team,
            req.combine_season,
            req.eval_season,
            cfb_season=req.cfb_season,
            consensus_extra_directories=_normalize_consensus_dirs(req.consensus_dirs),
        )
        return run_availability_and_recommendations(
            board,
            int(req.pick_number),
            n_simulations=min(5000, max(50, int(req.n_simulations))),
            temperature=float(req.temperature),
            available_ids=req.available_player_ids,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/draft/trade")
def api_draft_trade(req: DraftTradeRequest) -> Dict[str, Any]:
    from .draft.pipeline import build_draft_board
    from .draft.trade_simulator import best_trade_down_ranges

    try:
        board = build_draft_board(
            req.team,
            req.combine_season,
            req.eval_season,
            cfb_season=req.cfb_season,
            consensus_extra_directories=_normalize_consensus_dirs(req.consensus_dirs),
        )
        scan = best_trade_down_ranges(
            current_pick=int(req.current_pick),
            board_order=board["consensus_board"],
            prospects=board["prospects"],
            max_target=int(req.max_target_pick),
            target_player_ids=req.target_player_ids,
            n_simulations=min(800, max(100, int(req.n_simulations))),
        )
        return {
            "team": req.team,
            "current_pick": req.current_pick,
            "trade_down_scan": scan,
            "consensus_meta": board["meta"].get("consensus"),
        }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/draft/intelligence")
def api_draft_intelligence(req: DraftIntelligenceRequest) -> Dict[str, Any]:
    from .ai.draft_analyst import build_draft_intel_payload, generate_draft_analyst
    from .draft.pipeline import build_draft_board, run_availability_and_recommendations
    from .draft.report import build_draft_intelligence_report
    from .draft.trade_simulator import analyze_trade_down, best_trade_down_ranges

    try:
        board = build_draft_board(
            req.team,
            req.combine_season,
            req.eval_season,
            cfb_season=req.cfb_season,
            consensus_extra_directories=_normalize_consensus_dirs(req.consensus_dirs),
        )
        pack = run_availability_and_recommendations(
            board,
            int(req.pick_number),
            n_simulations=min(5000, max(50, int(req.n_simulations))),
            temperature=float(req.temperature),
            available_ids=None,
        )
        tgt = req.trade_target_pick
        if tgt is None:
            tgt = min(int(req.pick_number) + 10, int(req.pick_number) + 24)
        trade_summary = None
        if tgt > int(req.pick_number):
            top_ids = [str(r["player_id"]) for r in pack["recommendations"][:5]]
            trade_summary = analyze_trade_down(
                current_pick=int(req.pick_number),
                target_pick=int(tgt),
                board_order=board["consensus_board"],
                prospects=board["prospects"],
                target_player_ids=top_ids,
                n_simulations=min(600, int(req.n_simulations)),
                temperature=float(req.temperature),
            )
        scan = best_trade_down_ranges(
            current_pick=int(req.pick_number),
            board_order=board["consensus_board"],
            prospects=board["prospects"],
            max_target=min(int(req.pick_number) + 32, 260),
            target_player_ids=[str(r["player_id"]) for r in pack["recommendations"][:5]],
            n_simulations=min(400, int(req.n_simulations)),
        )
        report = build_draft_intelligence_report(
            board,
            pack["recommendations"],
            four_modes=pack.get("four_ranking_modes"),
            trade_summary=trade_summary,
            simulation=pack["simulation"],
        )
        ai_payload = build_draft_intel_payload(board, pack["recommendations"], pack["simulation"])
        analyst = generate_draft_analyst(ai_payload, ai_mode="template")
        return {
            "report": report,
            "trade_down_scan": scan[:8],
            "trade_detail": trade_summary,
            "four_ranking_modes": pack.get("four_ranking_modes"),
            "analyst": analyst,
        }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/draft/report")
def api_draft_report(req: DraftReportRequest) -> Any:
    """
    Build the draft board, render PDF(s) under ``outputs/reports/draft/``,
    and return ``/report-assets/draft/...`` URLs for the static mount.
    """
    from datetime import datetime, timezone
    from pathlib import Path

    from .draft.pipeline import build_draft_board, run_availability_and_recommendations
    from .reports.ai_content import get_content_generator
    from .reports.models import from_pipeline_output, prospect_dict_to_card
    from .reports.renderer import ReportRenderer

    repo_root = Path(__file__).resolve().parents[2]
    reports_root = (repo_root / "outputs" / "reports").resolve()
    draft_dir = reports_root / "draft"
    draft_dir.mkdir(parents=True, exist_ok=True)

    rt = (req.report_type or "all").strip().lower()
    if rt == "prospect" and not (req.prospect_name or "").strip():
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "prospect_name is required when report_type is 'prospect'",
            },
        )

    try:
        team_u = str(req.team).upper()
        combine_season = int(req.season) + 1
        board = build_draft_board(
            team_u,
            combine_season,
            int(req.season),
            draft_pick_positions=list(req.picks),
        )
        sim_picks = list(req.picks) if req.picks else [1]
        rec_by_pick: Dict[int, List[Any]] = {}
        for pick in sim_picks:
            pack = run_availability_and_recommendations(
                board,
                int(pick),
                n_simulations=800,
                temperature=2.0,
            )
            rec_by_pick[int(pick)] = pack["recommendations"]

        extended: Dict[str, Any] = dict(board)
        extended["recommendations_by_pick"] = rec_by_pick
        report = from_pipeline_output(
            extended,
            team_u,
            int(req.season),
            pick_slots=list(req.picks) if req.picks else None,
            top_n=int(req.top_n),
        )
        gen = get_content_generator(use_ai=bool(req.use_ai))
        renderer = ReportRenderer()
        out_paths: Dict[str, Path] = {}

        if rt == "needs":
            out_paths["needs"] = renderer.render_team_need_report(report, gen, draft_dir)
        elif rt == "board":
            out_paths["board"] = renderer.render_full_draft_board(
                report, gen, draft_dir, top_n_prospects=int(req.top_n)
            )
        elif rt == "prospect":
            q = (req.prospect_name or "").strip().lower()
            if not q:
                raise ValueError("prospect_name is required when report_type is 'prospect'")
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
                raise ValueError(f"No prospect matching {req.prospect_name!r} on the board.")
            out_paths["prospect"] = renderer.render_prospect_card(
                match_pc, report.team_snapshot, gen, draft_dir
            )
        else:
            out_paths = dict(renderer.render_all(report, gen, draft_dir, top_n_prospects=int(req.top_n)))

        def to_url(p: Path) -> str:
            rel = p.resolve().relative_to(reports_root)
            return "/report-assets/" + rel.as_posix()

        reports_urls = {k: to_url(v) for k, v in out_paths.items()}
        return {
            "status": "ok",
            "reports": reports_urls,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:  # noqa: BLE001
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@app.post("/api/ai/draft-analyst")
def api_ai_draft_analyst(req: DraftAnalystRequest) -> Dict[str, Any]:
    from .ai.draft_analyst import build_draft_intel_payload, generate_draft_analyst
    from .draft.pipeline import build_draft_board, run_availability_and_recommendations

    try:
        board = build_draft_board(
            req.team,
            req.combine_season,
            req.eval_season,
            cfb_season=req.cfb_season,
            consensus_extra_directories=_normalize_consensus_dirs(req.consensus_dirs),
        )
        pack = run_availability_and_recommendations(
            board,
            int(req.pick_number),
            n_simulations=min(5000, max(50, int(req.n_simulations))),
            temperature=float(req.temperature),
            available_ids=None,
        )
        payload = build_draft_intel_payload(board, pack["recommendations"], pack["simulation"])
        return generate_draft_analyst(payload, ai_mode=req.ai_mode)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/ai/config")
def api_ai_config() -> Dict[str, Any]:
    """
    Report current AI mode and whether Phi-4 repo is visible on disk.
    """
    import os
    from .ai.phi4_provider import Phi4Provider  # local import to avoid heavy side effects

    mode = os.getenv("GRIDIRONIQ_AI_MODE", "template").lower()
    provider = Phi4Provider()
    status = provider.status()
    return {
        "mode": mode,
        "phi4_repo_path": status["repo_path"],
        "phi4_model_path": status["model_path"],
        "phi4_available": status["available"],
        "phi4_loaded": status["loaded"],
        "multimodal_enabled": status["multimodal_enabled"],
        "fallback_active": mode != "phi4" or not status["available"],
    }


@app.get("/api/ai/health")
def api_ai_health() -> Dict[str, Any]:
    """
    Lightweight health check for the AI Statistician layer.
    """
    from .ai.template_provider import TemplateProvider

    template_ok = True
    try:
        ctx = ExplainerContext(matchup={}, scouting_report={})
        _ = TemplateProvider().generate(ctx)
    except Exception:
        template_ok = False

    from .ai.phi4_provider import Phi4Provider

    phi4 = Phi4Provider()
    status = phi4.status()

    # Optional: light smoke test for phi4 when available
    phi4_smoke_ok = False
    if status["available"]:
        try:
            ctx = ExplainerContext(matchup={}, scouting_report={})
            _ = phi4.generate(ctx)
            phi4_smoke_ok = True
        except Exception:
            phi4_smoke_ok = False

    return {
        "template_ok": template_ok,
        "phi4_repo_path": status["repo_path"],
        "phi4_model_path": status["model_path"],
        "phi4_available": status["available"],
        "phi4_loaded": status["loaded"],
        "multimodal_enabled": status["multimodal_enabled"],
        "phi4_smoke_ok": phi4_smoke_ok,
    }


@app.post("/api/matchup/run")
def api_run_matchup(req: MatchupRequest) -> Dict[str, Any]:
    """
    Run team-level matchup prediction using the wrapped SuperBowlEngine logic.
    """
    try:
        result: MatchupResult = run_matchup(
            season=req.season,
            team_a=req.team_a,
            team_b=req.team_b,
            mode=req.mode,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e

    manifest = load_logo_manifest()
    out = {
        "win_probability": result.win_probability,
        "predicted_winner": result.predicted_winner,
        "projected_score": result.projected_score,
        "projected_margin": result.projected_margin,
        "projected_total": result.projected_total,
        "team_efficiency_edges": result.team_efficiency_edges,
        "key_edges": result.key_edges,
        "keys_won": result.keys_won,
        "top_drivers": [list(p) for p in result.top_drivers],
        "team_a": result.team_a,
        "team_b": result.team_b,
        "season": result.season,
        "mode": result.mode,
        "team_a_logo": get_team_logo(result.team_a, manifest),
        "team_b_logo": get_team_logo(result.team_b, manifest),
    }
    return out


@app.post("/api/matchup/report")
def api_matchup_report(req: MatchupRequest) -> Dict[str, Any]:
    """
    Run matchup and return a structured scouting report (summary, strengths, profiles, notes).
    """
    try:
        result: MatchupResult = run_matchup(
            season=req.season,
            team_a=req.team_a,
            team_b=req.team_b,
            mode=req.mode,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e
    report = generate_report(result)
    manifest = load_logo_manifest()
    report["team_a_logo"] = get_team_logo(result.team_a, manifest)
    report["team_b_logo"] = get_team_logo(result.team_b, manifest)
    return report


@app.post("/api/qb/compare")
def api_qb_compare(req: QBCompareRequest) -> Dict[str, Any]:
    """
    Compare two quarterbacks using the QB production engine wrapper.
    """
    try:
        result: QBComparisonResult = compare_qbs(
            season=req.season,
            qb_a=req.qb_a,
            team_a=req.team_a,
            qb_b=req.qb_b,
            team_b=req.team_b,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "qb_a": result.qb_a,
        "team_a": result.team_a,
        "qb_b": result.qb_b,
        "team_b": result.team_b,
        "season": result.season,
        "sustain_score": result.sustain_score,
        "situational_score": result.situational_score,
        "offscript_score": result.offscript_score,
        "total_score": result.total_score,
        "avg_def_z": result.avg_def_z,
    }


@app.post("/api/backtest/run")
def api_backtest(req: BacktestRequest) -> Dict[str, Any]:
    """
    Run season-level backtest and return accuracy, score error, and calibration data.
    """
    try:
        result: BacktestResult = run_backtest(season=req.season)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e
    return result.to_dict()


# --- Report endpoints (Python-native reporting layer) ---


@app.post("/api/report/matchup")
def api_report_matchup(req: ReportMatchupRequest) -> Dict[str, Any]:
    """
    Build full matchup report: prediction, situational edges, offense vs defense, optional asset paths.
    """
    try:
        return build_matchup_report(
            season=req.season,
            team_a=req.team_a,
            team_b=req.team_b,
            week=req.week,
            mode=req.mode,
            generate_heatmaps=req.generate_heatmaps,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/report/broadcast")
def api_report_broadcast(req: ReportMatchupRequest) -> Dict[str, Any]:
    """
    Return broadcast-style report: headline stats, talking points, top 3 storylines.
    """
    try:
        return build_broadcast_report(
            season=req.season,
            team_a=req.team_a,
            team_b=req.team_b,
            week=req.week,
            generate_heatmaps=req.generate_heatmaps,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/report/presentation")
def api_report_presentation(req: ReportMatchupRequest) -> Dict[str, Any]:
    """
    Return presentation-style report: slides with bullets, key edges, visual refs.
    """
    try:
        return build_presentation_report(
            season=req.season,
            team_a=req.team_a,
            team_b=req.team_b,
            week=req.week,
            generate_heatmaps=req.generate_heatmaps,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/report/situational")
def api_report_situational(req: ReportMatchupRequest) -> Dict[str, Any]:
    """
    Return run/pass and situational tendency outputs for the matchup (no heatmap generation).
    """
    try:
        data = build_matchup_report(
            season=req.season,
            team_a=req.team_a,
            team_b=req.team_b,
            week=req.week,
            mode=req.mode,
            generate_heatmaps=False,
        )
        return {
            "team_a": data["team_a"],
            "team_b": data["team_b"],
            "season": data["season"],
            "situational_edges": data.get("situational_edges", {}),
            "offense_vs_defense": data.get("offense_vs_defense", {}),
        }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e

