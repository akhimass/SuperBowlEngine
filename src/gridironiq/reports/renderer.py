from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from jinja2 import Environment, FileSystemLoader

from .ai_content import FallbackContentGenerator, ReportContentGenerator
from .models import DraftBoardReport, ProspectCard, TeamNeedSnapshot

logger = logging.getLogger(__name__)


def _import_weasyprint() -> Any:
    try:
        import weasyprint as wp

        return wp
    except ImportError as e:
        raise ImportError(
            "WeasyPrint required for PDF generation. Run: pip install weasyprint"
        ) from e
    except OSError as e:  # pragma: no cover - platform-specific
        raise ImportError(
            "WeasyPrint could not load native libraries (e.g. Pango). "
            "See README Draft Room Reports for brew/apt install steps."
        ) from e


def _ensure_weasyprint() -> Any:
    return _import_weasyprint()


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


class ReportRenderError(Exception):
    """Raised when HTML → PDF conversion fails."""


def _render_html(template_name: str, context: Dict[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template(template_name)
    return template.render(**context)


render_template = _render_html


def _ts_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_filename_part(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", s).strip("_")[:80] or "player"


def _score_css_class(val: float) -> str:
    if val >= 80:
        return "score-green"
    if val >= 60:
        return "score-amber"
    return "score-red"


def _trend_arrow(v: float) -> str:
    if v > 0.0005:
        return "↑"
    if v < -0.0005:
        return "↓"
    return "→"


def _need_bar_class(score: float) -> str:
    if score > 75:
        return "bar-red"
    if score >= 50:
        return "bar-amber"
    return "bar-green"


def _pos_row_class(pos: str) -> str:
    p = (pos or "").upper()
    if p == "QB":
        return "pos-qb"
    if p in {"RB", "WR", "TE", "FB"}:
        return "pos-skill"
    if p in {"OT", "OG", "C", "IOL"} or p.startswith("O"):
        return "pos-ol"
    if p in {"EDGE", "DE", "DT", "IDL", "DL", "LB", "ILB", "OLB"}:
        return "pos-front"
    if p in {"CB", "SAF", "S", "DB", "FS", "SS"}:
        return "pos-db"
    return "pos-skill"


def _team_need_context(snapshot: TeamNeedSnapshot, executive_summary: str) -> Dict[str, Any]:
    need_rows = []
    for pos, score in snapshot.top_needs[:8]:
        need_rows.append(
            {
                "pos": pos,
                "score": score,
                "bar_pct": min(100.0, max(0.0, score)),
                "bar_class": _need_bar_class(score),
                "room_summary": snapshot.room_summaries.get(pos, ""),
            }
        )
    pr_raw = snapshot.scheme_summary.get("pass_rate", 0.0)
    try:
        pr = float(pr_raw)
    except (TypeError, ValueError):
        pr = 0.0
    te_tr = float(snapshot.scheme_summary.get("te_target_share_trend", 0.0) or 0.0)
    edge_tr = float(snapshot.scheme_summary.get("edge_pressure_trend", 0.0) or 0.0)
    return {
        "team": snapshot.team,
        "team_full_name": snapshot.team_full_name,
        "season": snapshot.season,
        "pick_slots": snapshot.pick_slots,
        "need_rows": need_rows,
        "executive_summary": executive_summary,
        "scheme_pass_pct": round(pr * 100.0, 1) if pr <= 1.5 else round(pr, 1),
        "te_trend_val": te_tr,
        "te_trend_arrow": _trend_arrow(te_tr),
        "edge_trend_val": edge_tr,
        "edge_trend_arrow": _trend_arrow(edge_tr),
        "signal_policy": snapshot.signal_policy,
        "signal_audit_rows": snapshot.signal_audit_rows,
        "generated_at": snapshot.generated_at,
    }


def _prospect_meas_dict(card: ProspectCard) -> Dict[str, str]:
    def fmt_f(x: Optional[float]) -> str:
        if x is None:
            return "—"
        return f"{x:.2f}"

    return {
        "forty": fmt_f(card.forty),
        "vertical": fmt_f(card.vertical),
        "broad": fmt_f(card.broad_jump),
        "bench": str(card.bench_press) if card.bench_press is not None else "—",
    }


def _score_bars_int(card: ProspectCard) -> List[Dict[str, Any]]:
    items = [
        ("Athleticism", card.athleticism_score),
        ("Production", card.production_score),
        ("Scheme fit", card.scheme_fit_score),
        ("Team need", card.team_need_score),
    ]
    out: List[Dict[str, Any]] = []
    for label, val in items:
        v = float(val)
        pct = int(round(min(100.0, max(0.0, v))))
        out.append({"label": label, "val": v, "pct": pct})
    return out


def _prod_rows_from_audit(card: ProspectCard) -> Tuple[List[Dict[str, str]], str, str]:
    cfb = card.audit_trail.get("cfb") if isinstance(card.audit_trail.get("cfb"), dict) else {}
    rows: List[Dict[str, str]] = []
    if cfb:
        for key in sorted(cfb.keys()):
            if key in {"cfb_conference", "conference", "production_source_detail"}:
                continue
            if key.startswith("cfb_") or key in {"season", "games", "yards", "td"}:
                val = cfb.get(key)
                if val is not None and str(val) not in {"", "nan"}:
                    rows.append({"k": key, "v": str(val)})
    rows = rows[-12:]
    if not rows:
        rows = [{"k": "CFB stats", "v": "Not loaded (optional CFBD key)"}]
    conf = str(cfb.get("cfb_conference") or cfb.get("conference") or card.conference or "—")
    try:
        cw = float(cfb.get("competition_weight", 1.0))
        cw_s = f"{cw:.2f}"
    except (TypeError, ValueError):
        cw_s = "1.00"
    return rows, conf, cw_s


def _scheme_audit_strings(card: ProspectCard) -> Tuple[Optional[str], Optional[str]]:
    detail = card.audit_trail.get("scheme_fit_detail")
    if not isinstance(detail, dict):
        return None, None
    arch = detail.get("te_archetype") or detail.get("archetype")
    fs = detail.get("scheme_fit_score")
    try:
        fit_s = f"{float(fs):.1f}" if fs is not None else None
    except (TypeError, ValueError):
        fit_s = None
    return (str(arch) if arch else None), fit_s


def _apply_prospect_narrative(
    card: ProspectCard,
    content_generator: Union[ReportContentGenerator, FallbackContentGenerator],
    snapshot: TeamNeedSnapshot,
    *,
    skip: bool = False,
) -> None:
    if skip:
        return
    bullets = content_generator.generate_prospect_bullets(card, snapshot)
    if isinstance(bullets.get("strengths"), list):
        card.strengths = [str(x) for x in bullets["strengths"]][:3]
    if isinstance(bullets.get("weaknesses"), list):
        card.weaknesses = [str(x) for x in bullets["weaknesses"]][:3]
    comp = bullets.get("comp")
    if isinstance(comp, str) and comp.strip():
        card.comp = comp.strip()
    ol = bullets.get("one_line")
    if isinstance(ol, str) and ol.strip():
        card.one_line = ol.strip()


def _sorted_prospects(report: DraftBoardReport) -> List[ProspectCard]:
    return sorted(report.top_prospects, key=lambda c: (-c.final_draft_score, c.name))


def _primary_prospect_for_pdf(report: DraftBoardReport) -> ProspectCard:
    if report.pick_recommendations:
        pk = min(report.pick_recommendations.keys())
        return report.pick_recommendations[pk]
    ranked = _sorted_prospects(report)
    if not ranked:
        raise ReportRenderError("No prospects available for prospect PDF")
    return ranked[0]


def _prefill_narratives(
    report: DraftBoardReport,
    content_generator: Union[ReportContentGenerator, FallbackContentGenerator],
    *,
    top_n: int,
) -> Tuple[str, int]:
    from .ai_content import MAX_AI_CALLS_PER_RUN

    max_calls = int(MAX_AI_CALLS_PER_RUN)

    snap = report.team_snapshot
    exec_txt = content_generator.generate_team_narrative(snap)
    n = max(0, int(top_n))
    cap = n
    if isinstance(content_generator, ReportContentGenerator):
        cap = min(n, max(0, max_calls - 2))
    done = 0
    for card in _sorted_prospects(report)[:cap]:
        _apply_prospect_narrative(card, content_generator, snap, skip=False)
        done += 1
    return exec_txt, done


class ReportRenderer:
    def _render_html(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a Jinja2 template under ``templates/`` to an HTML string (auto-escaping on)."""
        return _render_html(template_name, context)

    def _html_to_pdf(self, html: str, output_path: Path) -> Path:
        wp = _ensure_weasyprint()
        output_path = Path(output_path)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            wp.HTML(string=html).write_pdf(str(output_path))
        except Exception as e:  # noqa: BLE001
            raise ReportRenderError(f"WeasyPrint failed to write {output_path}: {e}") from e
        if not output_path.is_file() or output_path.stat().st_size <= 0:
            raise ReportRenderError(f"PDF missing or empty after write: {output_path}")
        logger.info("PDF written %s (%s bytes)", output_path, output_path.stat().st_size)
        return output_path

    def render_pdf(self, html_content: str, output_path: Path) -> Path:
        return self._html_to_pdf(html_content, output_path)

    def _build_prospect_context(
        self,
        card: ProspectCard,
        snapshot: TeamNeedSnapshot,
        generator: Union[ReportContentGenerator, FallbackContentGenerator],
    ) -> Dict[str, Any]:
        _apply_prospect_narrative(card, generator, snapshot, skip=False)
        prod_rows, conf_badge, comp_weight = _prod_rows_from_audit(card)
        scheme_archetype, scheme_fit_detail = _scheme_audit_strings(card)
        return {
            "card": card,
            "team": snapshot.team,
            "team_full_name": snapshot.team_full_name,
            "generated_at": snapshot.generated_at,
            "score_class": _score_css_class(card.final_draft_score),
            "score_bars": _score_bars_int(card),
            "meas": _prospect_meas_dict(card),
            "prod_rows": prod_rows,
            "conf_badge": conf_badge[:24],
            "comp_weight": comp_weight,
            "scheme_archetype": scheme_archetype,
            "scheme_fit_detail": scheme_fit_detail,
            "data_sources": "nflverse + model stack (see pipeline meta)",
            "report_title": f"{card.name} — Prospect card",
        }

    def render_team_need_report(
        self,
        report: DraftBoardReport,
        content_generator: Union[ReportContentGenerator, FallbackContentGenerator],
        output_dir: Path,
        *,
        executive_summary: Optional[str] = None,
    ) -> Path:
        snap = report.team_snapshot
        exec_txt = executive_summary
        if exec_txt is None:
            exec_txt = content_generator.generate_team_narrative(snap)
        ctx = {
            **_team_need_context(snap, exec_txt),
            "report_title": f"{snap.team_full_name} — Team need summary ({snap.season})",
        }
        html = self._render_html("team_need_report.html", ctx)
        out = Path(output_dir) / f"{snap.team}_{snap.season}_needs_{_ts_slug()}.pdf"
        return self._html_to_pdf(html, out)

    def render_prospect_card(
        self,
        card: ProspectCard,
        team_snapshot: TeamNeedSnapshot,
        content_generator: Union[ReportContentGenerator, FallbackContentGenerator],
        output_dir: Path,
        *,
        skip_narrative: bool = False,
    ) -> Path:
        if skip_narrative:
            prod_rows, conf_badge, comp_weight = _prod_rows_from_audit(card)
            scheme_archetype, scheme_fit_detail = _scheme_audit_strings(card)
            ctx = {
                "card": card,
                "team": team_snapshot.team,
                "team_full_name": team_snapshot.team_full_name,
                "generated_at": team_snapshot.generated_at,
                "score_class": _score_css_class(card.final_draft_score),
                "score_bars": _score_bars_int(card),
                "meas": _prospect_meas_dict(card),
                "prod_rows": prod_rows,
                "conf_badge": conf_badge[:24],
                "comp_weight": comp_weight,
                "scheme_archetype": scheme_archetype,
                "scheme_fit_detail": scheme_fit_detail,
                "data_sources": "nflverse + model stack (see pipeline meta)",
                "report_title": f"{card.name} — Prospect card",
            }
        else:
            ctx = self._build_prospect_context(card, team_snapshot, content_generator)
        html = self._render_html("prospect_card.html", ctx)
        slug = _safe_filename_part(card.name)
        pos = _safe_filename_part(card.position or "UNK")
        out = Path(output_dir) / f"{team_snapshot.team}_{team_snapshot.season}_{slug}_{pos}.pdf"
        return self._html_to_pdf(html, out)

    def render_full_draft_board(
        self,
        report: DraftBoardReport,
        content_generator: Union[ReportContentGenerator, FallbackContentGenerator],
        output_dir: Path,
        top_n_prospects: int = 10,
        *,
        executive_summary: Optional[str] = None,
        prospects_pre_narrated: bool = False,
        ai_narrated_prospect_count: int = 0,
    ) -> Path:
        snap = report.team_snapshot
        exec_txt = executive_summary
        if exec_txt is None:
            exec_txt = content_generator.generate_team_narrative(snap)
        trade = content_generator.generate_trade_scenarios(snap)
        report.trade_scenarios = trade

        recommended_names = {c.name.strip().lower() for c in report.pick_recommendations.values()}

        board_rows: List[Dict[str, Any]] = []
        sorted_board = _sorted_prospects(report)
        for i, card in enumerate(sorted_board, start=1):
            page_break = i > 1 and (i - 1) % 25 == 0
            av = card.availability_pct
            avail_s = f"{av:.0f}%" if av is not None else "—"
            board_rows.append(
                {
                    "page_break": page_break,
                    "rank": i,
                    "name": card.name,
                    "pos": card.position,
                    "college": card.college,
                    "score": card.final_draft_score,
                    "athl": card.athleticism_score,
                    "prod": card.production_score,
                    "fit": card.scheme_fit_score,
                    "need": card.team_need_score,
                    "avail": avail_s,
                    "recommended": card.name.strip().lower() in recommended_names,
                    "pos_class": _pos_row_class(card.position),
                }
            )

        fb = FallbackContentGenerator()
        prospect_pages: List[Dict[str, Any]] = []
        limit = max(0, int(top_n_prospects))
        for idx, card in enumerate(sorted_board[:limit]):
            if prospects_pre_narrated:
                if idx < ai_narrated_prospect_count:
                    _apply_prospect_narrative(card, content_generator, snap, skip=True)
                else:
                    _apply_prospect_narrative(card, fb, snap, skip=False)
            else:
                _apply_prospect_narrative(card, content_generator, snap, skip=False)
            prod_rows, conf_badge, comp_weight = _prod_rows_from_audit(card)
            scheme_archetype, scheme_fit_detail = _scheme_audit_strings(card)
            prospect_pages.append(
                {
                    "card": card,
                    "score_class": _score_css_class(card.final_draft_score),
                    "score_bars": _score_bars_int(card),
                    "meas": _prospect_meas_dict(card),
                    "prod_rows": prod_rows,
                    "conf_badge": conf_badge[:24],
                    "comp_weight": comp_weight,
                    "scheme_archetype": scheme_archetype,
                    "scheme_fit_detail": scheme_fit_detail,
                    "data_sources": "nflverse + model stack",
                }
            )

        base_ctx = _team_need_context(snap, exec_txt)
        ctx = {
            **base_ctx,
            "report_title": report.report_title,
            "board_rows": board_rows,
            "prospect_pages": prospect_pages,
            "trade_scenarios": trade,
        }
        html = self._render_html("draft_board.html", ctx)
        out = Path(output_dir) / f"{snap.team}_{snap.season}_draftboard_{_ts_slug()}.pdf"
        return self._html_to_pdf(html, out)

    def render_all(
        self,
        report: DraftBoardReport,
        content_generator: Union[ReportContentGenerator, FallbackContentGenerator],
        output_dir: Path,
        *,
        top_n_prospects: int = 10,
    ) -> Dict[str, Path]:
        out_dir = Path(output_dir)
        ranked = _sorted_prospects(report)
        if not ranked:
            raise ReportRenderError("render_all requires at least one prospect for prospect PDF")
        n = max(1, int(top_n_prospects))
        exec_txt, ai_done = _prefill_narratives(report, content_generator, top_n=n)
        needs_path = self.render_team_need_report(
            report, content_generator, out_dir, executive_summary=exec_txt
        )
        top = _primary_prospect_for_pdf(report)
        prospect_path = self.render_prospect_card(
            top,
            report.team_snapshot,
            content_generator,
            out_dir,
            skip_narrative=True,
        )
        board_path = self.render_full_draft_board(
            report,
            content_generator,
            out_dir,
            top_n_prospects=n,
            executive_summary=exec_txt,
            prospects_pre_narrated=True,
            ai_narrated_prospect_count=ai_done,
        )
        return {
            "needs": needs_path,
            "prospect": prospect_path,
            "board": board_path,
        }
