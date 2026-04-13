from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .models import ProspectCard, TeamNeedSnapshot

logger = logging.getLogger(__name__)

MAX_AI_CALLS_PER_RUN = 10
AI_TIMEOUT_SEC = 15.0
_DRAFT_LOG_PATH = Path("outputs/reports/draft/logs/ai_calls.jsonl")


def _log_ai_line(entry: Dict[str, Any]) -> None:
    try:
        _DRAFT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with _DRAFT_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError as e:
        logger.warning("Could not write AI log %s: %s", _DRAFT_LOG_PATH, e)


def _call_with_timeout(fn: Any, timeout_sec: float, *args: Any, **kwargs: Any) -> Any:
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(fn, *args, **kwargs)
        return fut.result(timeout=timeout_sec)


class ReportContentGenerator:
    """
    Local Phi-4 text via ``Phi4Provider._raw_generate`` only (no ``generate(ExplainerContext)``).
    Lazy provider init; never raises from public methods.
    """

    def __init__(self) -> None:
        self._phi4: Optional[Any] = None
        self._phi4_attempted = False
        self._call_count = 0
        self._max_calls = 10

    def _get_phi4(self) -> Optional[Any]:
        if self._phi4_attempted:
            return self._phi4
        self._phi4_attempted = True
        try:
            import torch  # noqa: F401
        except ImportError:
            self._phi4 = None
            return None
        try:
            from gridironiq.ai.phi4_provider import Phi4Provider

            prov = Phi4Provider()
            if not prov.status().get("available"):
                self._phi4 = None
                return None
            self._phi4 = prov
            return prov
        except Exception as e:  # noqa: BLE001
            logger.debug("Phi4Provider unavailable: %s", e)
            self._phi4 = None
            return None

    def _call_phi4(self, prompt: str, max_tokens: int = 512) -> Optional[str]:
        if self._call_count >= self._max_calls:
            return None
        phi = self._get_phi4()
        if phi is None:
            return None
        self._call_count += 1
        call_number = self._call_count
        t0 = time.perf_counter()
        success = False
        response = ""
        try:
            response = _call_with_timeout(
                phi._raw_generate,  # noqa: SLF001
                AI_TIMEOUT_SEC,
                prompt,
                max_tokens,
            )
            response = str(response or "").strip()
            success = bool(response)
        except FuturesTimeout:
            logger.warning("Phi-4 report call timed out after %ss", AI_TIMEOUT_SEC)
        except Exception as e:  # noqa: BLE001
            logger.exception("Phi-4 report call failed: %s", e)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        _log_ai_line(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "prompt_preview": (prompt[:200] + ("…" if len(prompt) > 200 else "")),
                "response_preview": (response[:200] + ("…" if len(response) > 200 else "")),
                "latency_ms": latency_ms,
                "success": success,
                "call_number": call_number,
            }
        )
        return response if success else None

    def _parse_json_response(self, raw: str) -> Dict[str, Any]:
        if not raw:
            return {}
        text = raw.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            pass
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    def generate_prospect_bullets(
        self,
        card: ProspectCard,
        snapshot: TeamNeedSnapshot,
    ) -> Dict[str, Any]:
        top3 = snapshot.top_needs[:3]
        needs_txt = ", ".join(f"{p}:{s:.1f}" for p, s in top3)
        prompt = (
            f"Prospect: {card.name} | {card.position} | {card.college}\n"
            f"Measurables: H {card.height} Wt {card.weight} 40 {card.forty} VJ {card.vertical} "
            f"BJ {card.broad_jump} Bench {card.bench_press}\n"
            f"Scores: prospect {card.prospect_score:.1f} athletic {card.athleticism_score:.1f} "
            f"production {card.production_score:.1f} scheme_fit {card.scheme_fit_score:.1f} "
            f"need {card.team_need_score:.1f} final {card.final_draft_score:.1f}\n"
            f"Team top 3 needs: {needs_txt}\n\n"
            "Respond ONLY with valid JSON. No markdown. No preamble. "
            "Keys: strengths (list of 3 strings), weaknesses (list of 3 strings), "
            "comp (string), one_line (string).\n"
        )
        raw = self._call_phi4(prompt, max_tokens=512)
        data = self._parse_json_response(raw or "") if raw else {}
        fb = FallbackContentGenerator()
        if not data:
            return fb.generate_prospect_bullets(card, snapshot)

        def _three(key: str) -> List[str]:
            v = data.get(key)
            if isinstance(v, list):
                return [str(x).strip() for x in v[:3] if str(x).strip()]
            return []

        strengths = _three("strengths")
        weaknesses = _three("weaknesses")
        comp = str(data.get("comp") or "").strip()
        one_line = str(data.get("one_line") or "").strip()
        if len(strengths) != 3 or len(weaknesses) != 3 or not comp or not one_line:
            return fb.generate_prospect_bullets(card, snapshot)
        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "comp": comp,
            "one_line": one_line,
        }

    def generate_team_narrative(self, snapshot: TeamNeedSnapshot) -> str:
        scheme_txt = json.dumps(snapshot.scheme_summary, ensure_ascii=False)
        needs_txt = ", ".join(f"{p}:{s:.1f}" for p, s in snapshot.top_needs[:5])
        prompt = (
            f"Team: {snapshot.team_full_name} ({snapshot.team}) season {snapshot.season}\n"
            f"Picks: {snapshot.pick_slots}\n"
            f"Top needs: {needs_txt}\n"
            f"Scheme/trends (JSON): {scheme_txt}\n\n"
            "Respond with plain text only. No JSON. No markdown. 3-4 sentences maximum.\n"
            "Ground every sentence in the data above.\n"
        )
        raw = self._call_phi4(prompt, max_tokens=256)
        text = re.sub(r"\s+", " ", (raw or "").strip())[:1200]
        if len(text) < 40:
            return FallbackContentGenerator().generate_team_narrative(snapshot)
        return text

    def generate_pick_narrative(
        self,
        pick_slot: int,
        card: ProspectCard,
        snapshot: TeamNeedSnapshot,
    ) -> str:
        needs_txt = ", ".join(f"{p}:{s:.1f}" for p, s in snapshot.top_needs[:4])
        prompt = (
            f"Team: {snapshot.team_full_name} ({snapshot.team}) | Pick: {pick_slot}\n"
            f"Candidate: {card.name} ({card.position}) final {card.final_draft_score:.1f} "
            f"avail% {card.availability_pct}\n"
            f"Top needs: {needs_txt}\n\n"
            "Plain text only. 2-3 sentences. No JSON. No markdown.\n"
        )
        raw = self._call_phi4(prompt, max_tokens=200)
        text = re.sub(r"\s+", " ", (raw or "").strip())[:800]
        if len(text) < 30:
            return FallbackContentGenerator().generate_pick_narrative(pick_slot, card, snapshot)
        return text

    def generate_trade_scenarios(self, snapshot: TeamNeedSnapshot) -> List[str]:
        return FallbackContentGenerator().generate_trade_scenarios(snapshot)


class FallbackContentGenerator:
    """Data-driven copy; no model calls."""

    def generate_prospect_bullets(
        self,
        card: ProspectCard,
        snapshot: TeamNeedSnapshot,
    ) -> Dict[str, Any]:
        scores = [
            ("athleticism", card.athleticism_score),
            ("production", card.production_score),
            ("scheme_fit", card.scheme_fit_score),
            ("team_need", card.team_need_score),
        ]
        strengths: List[str] = []
        for label, val in scores:
            if label == "athleticism" and val > 80:
                strengths.append(
                    "Elite combine profile — top-percentile speed and explosion for the position."
                )
            elif label == "production" and val > 75:
                strengths.append(
                    "Strong college production efficiency relative to competition level in the model."
                )
            elif label == "scheme_fit" and val > 70:
                strengths.append(
                    "Scheme alignment with the team's offensive/defensive usage profile."
                )
            elif label == "team_need" and val > 75:
                strengths.append("Directly addresses a critical roster need bucket.")
        while len(strengths) < 3:
            strengths.append(
                f"Balanced composite grade (prospect score {card.prospect_score:.1f}) across subcomponents."
            )
        strengths = strengths[:3]

        weaknesses: List[str] = []
        for label, val in scores:
            if label == "production" and val < 50:
                weaknesses.append("Production metrics sit below an elite threshold for the position.")
            elif label == "athleticism" and val < 55:
                weaknesses.append("Athletic testing does not stand out versus combine peers.")
            elif label == "scheme_fit" and val < 55:
                weaknesses.append("Scheme-fit signal is soft relative to team tendencies.")
        av = card.availability_pct
        if av is None or av < 40:
            weaknesses.append("Board position creates availability risk at this pick slot.")
        while len(weaknesses) < 3:
            weaknesses.append("Monitor off-model factors (medical, character) outside this data stack.")
        weaknesses = weaknesses[:3]

        comp = f"{card.position} contributor"
        fs = card.final_draft_score
        if fs > 80:
            tier = "first-round"
        elif fs > 65:
            tier = "strong day-2"
        else:
            tier = "developmental"
        top_need = snapshot.top_needs[0][0] if snapshot.top_needs else "roster"
        one_line = (
            f"{card.name} projects as a {top_need} addition for {snapshot.team_full_name} "
            f"with a {tier} grade."
        )
        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "comp": comp,
            "one_line": one_line,
        }

    def generate_team_narrative(self, snapshot: TeamNeedSnapshot) -> str:
        t1 = snapshot.top_needs[0] if snapshot.top_needs else ("need", 0.0)
        t2 = snapshot.top_needs[1] if len(snapshot.top_needs) > 1 else t1
        pr = float(snapshot.scheme_summary.get("pass_rate") or 0.0)
        scheme_note = f"{pr * 100:.1f}% pass-rate" if pr else "balanced"
        first_pick = snapshot.pick_slots[0] if snapshot.pick_slots else 1
        n_picks = len(snapshot.pick_slots)
        n_rounds = max(1, min(7, n_picks))
        return (
            f"{snapshot.team_full_name} enter the {snapshot.season} draft at pick {first_pick} "
            f"with {t1[0]} and {t2[0]} as their primary targets. "
            f"The {scheme_note} scheme identity informs their board preferences. "
            f"With {n_picks} selections across {n_rounds} rounds, the front office has capital "
            f"to address multiple needs."
        )

    def generate_pick_narrative(
        self,
        pick_slot: int,
        card: ProspectCard,
        snapshot: TeamNeedSnapshot,
    ) -> str:
        ol = card.one_line or f"{card.name} grades {card.final_draft_score:.1f} on the model board."
        return (
            f"{card.name} represents strong value for {snapshot.team_full_name} at pick {pick_slot}. "
            f"{ol} The {snapshot.team_full_name} draft the best player available who addresses "
            f"a clear positional need."
        )

    def generate_trade_scenarios(self, snapshot: TeamNeedSnapshot) -> List[str]:
        return [
            f"If the board runs early at {snapshot.top_needs[0][0] if snapshot.top_needs else 'need'}, "
            f"consider trading back to add picks.",
            f"With slots {snapshot.pick_slots}, packaging capital only makes sense when a tier break aligns.",
        ]


def get_content_generator(use_ai: bool = True) -> Union[ReportContentGenerator, FallbackContentGenerator]:
    if use_ai:
        return ReportContentGenerator()
    return FallbackContentGenerator()
