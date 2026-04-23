from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any, Dict, Optional

from .schemas import ExplainerContext

logger = logging.getLogger(__name__)


def build_chat_prompt(question: str, ctx: ExplainerContext) -> str:
    """
    A strict, grounded chat prompt: answer ONLY using the provided context JSON.
    If out-of-scope, refuse and ask for a question about the current matchup/game.
    """
    if ctx.draft_intel:
        context_json = json.dumps(ctx.draft_intel, ensure_ascii=False)
        return (
            "You are GridironIQ's AI Draft Analyst.\n"
            "Rules:\n"
            "- You MUST answer using ONLY the JSON draft context below (nflverse-backed board).\n"
            "- Do NOT invent medical info, rumors, or agents.\n"
            "- If the question is not about this draft board, refuse briefly and suggest 2 in-scope questions.\n"
            "- Keep it concise: 4-10 sentences, plus up to 5 bullets if helpful.\n"
            "\n"
            f"QUESTION:\n{question}\n\n"
            f"DRAFT_CONTEXT_JSON:\n{context_json}\n\n"
            "ANSWER:"
        )

    context_json = json.dumps(asdict(ctx), ensure_ascii=False)
    return (
        "You are GridironIQ's AI Statistician.\n"
        "Rules:\n"
        "- You MUST answer using ONLY the JSON context provided below.\n"
        "- Do NOT invent stats or players.\n"
        "- If the question cannot be answered from context, say: "
        "\"I can only answer questions about the currently loaded matchup/report context.\" "
        "and suggest 2 relevant questions.\n"
        "- Keep it concise: 4-10 sentences, plus up to 5 bullets if helpful.\n"
        "\n"
        f"QUESTION:\n{question}\n\n"
        f"CONTEXT_JSON:\n{context_json}\n\n"
        "ANSWER:"
    )


def generate_ai_chat_answer(
    *,
    question: str,
    context: ExplainerContext,
    ai_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return a grounded chat answer with provider metadata.
    """
    mode = (ai_mode or "").lower().strip() or None
    resolved = mode
    if resolved not in {None, "template", "phi4"}:
        resolved = None

    prompt = build_chat_prompt(question, context)

    if resolved == "phi4":
        from .phi4_provider import Phi4Provider

        provider = Phi4Provider()
        try:
            raw = provider._raw_generate(prompt, max_new_tokens=256)  # noqa: SLF001
            text = raw.strip()
            if not text:
                raise RuntimeError("empty phi4 output")
            return {"answer": text, "provider": "phi4", "fallback": False}
        except Exception as e:  # noqa: BLE001
            logger.exception("Phi-4 chat failed; falling back: %s", e)
            resolved = "template"

    # Draft room: template grounded on board JSON only
    if context.draft_intel:
        recs = context.draft_intel.get("recommendations") or []
        team = context.draft_intel.get("team", "")
        pick = context.draft_intel.get("pick_number", "")
        needs = context.draft_intel.get("team_need_scores") or {}
        top = recs[0] if recs else {}
        alts = recs[1:3]
        ql = question.lower()
        base = (
            f"{team} draft room (pick {pick}). "
            f"Top levered target: {top.get('player_name', 'n/a')} ({top.get('pos', '')}) "
            f"final ~{top.get('final_draft_score')} | availability ~{top.get('availability_at_pick')}.\n"
        )
        if any(k in ql for k in ["pass", "wait", "trade", "later", "reach"]):
            base += (
                "If you pass, check the next levered names and their availability percentages "
                "in the recommendations list — high availability lowers urgency at this pick.\n"
            )
        if any(k in ql for k in ["risk", "bust", "injury", "character"]):
            base += (
                "Risk in this view is structural: grades combine nflverse athletic testing, "
                "career efficiency where published, team EPA need, and scheme fit — not medical intel.\n"
            )
        if any(k in ql for k in ["need", "panther", "car", "hole", "depth"]):
            need_txt = ", ".join(f"{k}:{round(v,1)}" for k, v in sorted(needs.items(), key=lambda x: -x[1])[:5])
            base += f"Top positional need scores (0–100): {need_txt}.\n"
        if alts:
            base += "Alternates: " + ", ".join(
                f"{a.get('player_name')} ({a.get('pos')})" for a in alts if a.get("player_name")
            )
            + ".\n"
        return {"answer": base, "provider": "template", "fallback": True}

    # Template fallback: grounded response from report fields only
    m = context.matchup or {}
    r = context.scouting_report or {}
    team_a = m.get("team_a") or r.get("team_a")
    team_b = m.get("team_b") or r.get("team_b")
    winner = m.get("predicted_winner") or r.get("predicted_winner")
    wp = m.get("win_probability") or r.get("win_probability")
    top = (r.get("top_drivers") or m.get("top_drivers") or [])[:3]
    summary = r.get("summary") or ""

    # Guardrail: keep in-scope only
    answer = (
        "I can only answer questions about the currently loaded matchup/report context.\n\n"
        f"Context snapshot: {team_a} vs {team_b}, predicted winner {winner} with win probability {wp}.\n"
    )
    # If user asked a relevant question, give a helpful grounded response.
    ql = question.lower()
    if any(k in ql for k in ["why", "favor", "edge", "driver", "margin", "total", "score", "red zone", "third down", "turnover", "epa"]):
        reasons = []
        for d in top:
            if isinstance(d, list) and len(d) == 2:
                reasons.append(f"- {d[0]} (impact {d[1]})")
            elif isinstance(d, str):
                reasons.append(f"- {d}")
        answer = (
            f"{team_a} vs {team_b}: the model leans {winner} at ~{round(float(wp or 0) * 100, 1)}%.\n"
            f"{(summary[:220] + '…') if len(summary) > 220 else summary}\n\n"
            "Top drivers available in the report:\n"
            + ("\n".join(reasons) if reasons else "- (no driver list available)")
            + "\n\nAsk next:\n"
            "- What matters most in the red zone for this matchup?\n"
            "- Which efficiency edge is doing the most work in the prediction?\n"
        )

    return {"answer": answer, "provider": "template", "fallback": True}

