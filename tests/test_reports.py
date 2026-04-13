from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from gridironiq.reports.ai_content import FallbackContentGenerator, ReportContentGenerator, get_content_generator
from gridironiq.reports.models import (
    TEAM_NAMES,
    DraftBoardReport,
    ProspectCard,
    TeamNeedSnapshot,
    from_pipeline_output,
    prospect_dict_to_card,
)
from gridironiq.reports.renderer import ReportRenderer, render_template


def _fake_team_needs(team: str = "KC") -> dict:
    need_scores = {b: float(50 + i * 2) for i, b in enumerate(["QB", "RB", "WR", "TE", "OT"])}
    return {
        "team": team,
        "season": 2025,
        "need_scores": need_scores,
        "signal_layers": {
            "epa_need_normalized": {k: 40.0 for k in need_scores},
            "snap_depth_normalized": {k: 30.0 for k in need_scores},
            "injury_pressure_normalized": {k: 10.0 for k in need_scores},
            "room_production_normalized": {k: 35.0 for k in need_scores},
        },
        "need_signal_policy": {
            "manual_need_priors": False,
            "sources": ["nflverse_pbp_epa", "nflverse_snap_counts"],
            "team": team,
            "season": 2025,
        },
        "epa_profile": {},
    }


def _fake_prospect(name: str = "Test Player", pid: str = "p1") -> dict:
    return {
        "player_id": pid,
        "player_name": name,
        "pos": "WR",
        "school": "Test U",
        "height": "6-1",
        "weight_lb": 200.0,
        "forty": 4.45,
        "vertical": 36.0,
        "broad_jump": 125.0,
        "bench": 12.0,
        "prospect_score": 72.0,
        "team_need_score": 65.0,
        "scheme_fit_score": 70.0,
        "final_draft_score": 75.0,
        "radar": {
            "athleticism": 80.0,
            "production": 68.0,
            "scheme_fit": 70.0,
            "team_need": 65.0,
        },
        "score_breakdown": {
            "prospect": {
                "prospect_score": 72.0,
                "athletic_score": 80.0,
                "production_score": 68.0,
                "efficiency_score": 66.0,
                "age_adjustment": 55.0,
                "production_source": "test",
            },
            "fusion": {"final_draft_score": 75.0},
            "scheme_fit_detail": {"te_archetype": "move", "scheme_fit_score": 70.0},
            "cfb": {"cfb_conference": "SEC", "competition_weight": 1.05, "cfb_yards": 900},
        },
    }


def _fake_board(team: str = "KC", season: int = 2025) -> dict:
    return {
        "team": team,
        "eval_season": season,
        "combine_season": season + 1,
        "team_needs": _fake_team_needs(team),
        "team_scheme": {"raw": {"off_pass_rate": 0.58, "te_target_share": 0.18}},
        "team_context_summary": {
            "team": team,
            "season": season,
            "top_needs": [{"bucket": "WR", "score": 80.0}],
            "scheme_highlights": {
                "pass_rate": 0.58,
                "te_target_share_trend": 0.001,
                "edge_pressure_trend": -0.002,
            },
            "need_signal_policy": _fake_team_needs(team)["need_signal_policy"],
            "draft_pick_positions": [19, 51],
        },
        "prospects": [_fake_prospect()],
        "consensus_board": [],
        "meta": {"data_sources": ["test"]},
    }


def _snapshot_for_fallback(team: str = "KC") -> TeamNeedSnapshot:
    return TeamNeedSnapshot(
        team=team,
        team_full_name=TEAM_NAMES.get(team, team),
        season=2025,
        pick_slots=[23, 54],
        top_needs=[("WR", 80.0), ("CB", 70.0)],
        scheme_summary={"pass_rate": 0.55},
        room_summaries={"WR": "room note"},
        signal_policy="data_only",
        generated_at="2025-01-01T00:00:00+00:00",
    )


def test_from_pipeline_output_ok() -> None:
    board = _fake_board()
    r = from_pipeline_output(board, "KC", 2025)
    assert isinstance(r, DraftBoardReport)
    assert r.team_snapshot.team == "KC"
    assert len(r.top_prospects) >= 1


def test_from_pipeline_output_top_n_cap() -> None:
    b = _fake_board()
    p1 = _fake_prospect("Higher Score", "p1")
    p2 = _fake_prospect("Lower Score", "p2")
    p1["final_draft_score"] = 92.0
    p2["final_draft_score"] = 48.0
    b["prospects"] = [p2, p1]
    r = from_pipeline_output(b, "KC", 2025, top_n=1)
    assert len(r.top_prospects) == 1
    assert r.top_prospects[0].name == "Higher Score"


def test_from_pipeline_output_missing_prospects_key() -> None:
    b = _fake_board()
    del b["prospects"]
    with pytest.raises(ValueError, match="Missing required key: prospects"):
        from_pipeline_output(b, "KC", 2025)


def test_from_pipeline_output_missing_keys() -> None:
    with pytest.raises(ValueError, match="eval_season"):
        from_pipeline_output({"team": "KC", "prospects": [_fake_prospect()]}, "KC", 2025)
    with pytest.raises(ValueError, match="prospects"):
        b = _fake_board()
        b["prospects"] = []
        from_pipeline_output(b, "KC", 2025)
    with pytest.raises(ValueError, match="team_context_summary"):
        b = _fake_board()
        del b["team_context_summary"]
        from_pipeline_output(b, "KC", 2025)


def test_prospect_card_to_dict_json_serializable() -> None:
    row = _fake_prospect()
    card = prospect_dict_to_card(row)
    d = card.to_dict()
    json.dumps(d)


def test_fallback_prospect_bullets() -> None:
    fb = FallbackContentGenerator()
    card = prospect_dict_to_card(_fake_prospect())
    snap = _snapshot_for_fallback()
    out = fb.generate_prospect_bullets(card, snap)
    assert {"strengths", "weaknesses", "comp", "one_line"}.issubset(out.keys())
    assert len(out["strengths"]) == 3
    assert len(out["weaknesses"]) == 3
    assert all(isinstance(s, str) and s.strip() for s in out["strengths"])
    assert all(isinstance(s, str) and s.strip() for s in out["weaknesses"])
    assert str(out["comp"]).strip()
    assert str(out["one_line"]).strip()


def test_fallback_team_narrative() -> None:
    fb = FallbackContentGenerator()
    snap = _snapshot_for_fallback()
    t = fb.generate_team_narrative(snap)
    assert isinstance(t, str) and len(t) > 20


def test_fallback_pick_narrative() -> None:
    fb = FallbackContentGenerator()
    snap = _snapshot_for_fallback()
    card = prospect_dict_to_card(_fake_prospect())
    t = fb.generate_pick_narrative(19, card, snap)
    assert isinstance(t, str) and len(t) > 30


def test_render_template_team_need() -> None:
    snap = TeamNeedSnapshot(
        team="KC",
        team_full_name="Kansas City Chiefs",
        season=2025,
        pick_slots=[23, 54],
        top_needs=[("WR", 80.0), ("CB", 70.0)],
        scheme_summary={"pass_rate": 0.55, "te_target_share_trend": 0.01, "edge_pressure_trend": -0.01},
        room_summaries={"WR": "Note WR", "CB": "Note CB"},
        signal_policy="data_only | sources=[]",
        generated_at="2025-01-01T00:00:00+00:00",
        signal_audit_rows=[{"signal_source": "t", "weight": 1.0, "contribution": "c"}],
    )
    from gridironiq.reports.renderer import _team_need_context

    ctx = {
        **_team_need_context(snap, "Executive summary sentence one. Two. Three."),
        "report_title": "Test",
    }
    html = render_template("team_need_report.html", ctx)
    assert "<html" in html.lower()


def test_renderer_instance_render_html() -> None:
    snap = TeamNeedSnapshot(
        team="KC",
        team_full_name="Kansas City Chiefs",
        season=2025,
        pick_slots=[23, 54],
        top_needs=[("WR", 80.0), ("CB", 70.0)],
        scheme_summary={"pass_rate": 0.55},
        room_summaries={"WR": "Note WR", "CB": "Note CB"},
        signal_policy="data_only",
        generated_at="2025-01-01T00:00:00+00:00",
    )
    from gridironiq.reports.renderer import _team_need_context

    r = ReportRenderer()
    ctx = {
        **_team_need_context(snap, "Summary."),
        "report_title": "Test",
    }
    html = r._render_html("team_need_report.html", ctx)
    assert "<html" in html.lower()


def test_render_template_prospect_optional_none() -> None:
    card = ProspectCard(
        name="A B",
        position="QB",
        college="State",
        conference="—",
        height="—",
        weight=0,
        forty=None,
        vertical=None,
        broad_jump=None,
        bench_press=None,
        prospect_score=50.0,
        athleticism_score=50.0,
        production_score=50.0,
        scheme_fit_score=50.0,
        team_need_score=50.0,
        final_draft_score=55.0,
        availability_pct=None,
        strengths=["s1", "s2", "s3"],
        weaknesses=["w1", "w2", "w3"],
        comp=None,
        one_line=None,
        audit_trail={},
    )
    ctx = {
        "card": card,
        "team": "KC",
        "team_full_name": "Kansas City Chiefs",
        "generated_at": "2025-01-01T00:00:00+00:00",
        "score_class": "score-amber",
        "score_bars": [{"label": "Athleticism", "val": 50.0, "pct": 50.0}],
        "meas": {"forty": "—", "vertical": "—", "broad": "—", "bench": "—"},
        "prod_rows": [{"k": "k", "v": "v"}],
        "conf_badge": "SEC",
        "comp_weight": "1.0",
        "scheme_archetype": None,
        "scheme_fit_detail": None,
        "data_sources": "test",
        "report_title": "t",
    }
    html = render_template("prospect_card.html", ctx)
    assert "A B" in html


def test_render_pdf_and_render_all(tmp_path: Path) -> None:
    from gridironiq.reports.renderer import _import_weasyprint

    try:
        _import_weasyprint()
    except ImportError:
        pytest.skip("WeasyPrint or native PDF libraries unavailable")

    r = ReportRenderer()
    out = tmp_path / "pdf_out"
    out.mkdir()
    path = out / "minimal_test.pdf"
    html = "<html><body><p>Hi</p></body></html>"
    written = r.render_pdf(html, path)
    assert written.is_file() and written.stat().st_size > 0

    rep = from_pipeline_output(_fake_board(), "KC", 2025)
    gen = get_content_generator(use_ai=False)
    paths = r.render_all(rep, gen, out, top_n_prospects=1)
    assert set(paths.keys()) == {"needs", "prospect", "board"}
    for p in paths.values():
        assert p.is_file() and "KC" in p.name and "2025" in p.name


def test_render_team_need_pdf_substantial(tmp_path: Path) -> None:
    from gridironiq.reports.renderer import _import_weasyprint

    try:
        _import_weasyprint()
    except ImportError:
        pytest.skip("WeasyPrint or native PDF libraries unavailable")

    r = ReportRenderer()
    rep = from_pipeline_output(_fake_board(), "KC", 2025)
    gen = get_content_generator(use_ai=False)
    p = r.render_team_need_report(rep, gen, tmp_path)
    assert p.is_file()
    assert p.stat().st_size > 1000
    assert "KC" in p.name and "2025" in p.name


@pytest.mark.slow
def test_pipeline_report_smoke_subprocess(tmp_path: Path) -> None:
    if not os.environ.get("GRIDIRONIQ_RUN_PIPELINE_REPORT"):
        pytest.skip("Set GRIDIRONIQ_RUN_PIPELINE_REPORT=1 to run nflverse pipeline PDF smoke test")
    from gridironiq.reports.renderer import _import_weasyprint

    try:
        _import_weasyprint()
    except ImportError:
        pytest.skip("WeasyPrint or native PDF libraries unavailable")
    import subprocess
    import sys

    out = tmp_path / "out"
    out.mkdir()
    cmd = [
        sys.executable,
        "-m",
        "gridironiq.draft.pipeline",
        "--team",
        "KC",
        "--season",
        "2025",
        "--picks",
        "23",
        "--top-n",
        "1",
        "--report",
        "--report-type",
        "needs",
        "--no-ai",
        "--report-output-dir",
        str(out),
    ]
    subprocess.run(cmd, check=True, cwd=Path(__file__).resolve().parents[1])
    pdfs = list(out.glob("*.pdf"))
    assert pdfs
    assert any("KC" in p.name and "2025" in p.name for p in pdfs)


def test_get_content_generator_modes() -> None:
    assert isinstance(get_content_generator(use_ai=False), FallbackContentGenerator)
    assert isinstance(get_content_generator(use_ai=True), ReportContentGenerator)


def test_team_names_completeness() -> None:
    assert len(TEAM_NAMES) == 32
    assert TEAM_NAMES["CAR"] == "Carolina Panthers"
    assert TEAM_NAMES["KC"] == "Kansas City Chiefs"


def test_phi4_unavailable_no_ai_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import gridironiq.reports.ai_content as ac

    log_path = tmp_path / "ai_calls.jsonl"
    monkeypatch.setattr(ac, "_DRAFT_LOG_PATH", log_path)
    gen = ReportContentGenerator()
    monkeypatch.setattr(gen, "_get_phi4", lambda: None)
    assert gen._call_phi4("test prompt for logging") is None  # noqa: SLF001
    assert not log_path.exists()


def test_fallback_does_not_write_ai_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import gridironiq.reports.ai_content as ac

    log_path = tmp_path / "ai_calls.jsonl"
    monkeypatch.setattr(ac, "_DRAFT_LOG_PATH", log_path)
    fb = FallbackContentGenerator()
    snap = _snapshot_for_fallback()
    card = prospect_dict_to_card(_fake_prospect())
    fb.generate_prospect_bullets(card, snap)
    assert not log_path.exists()
