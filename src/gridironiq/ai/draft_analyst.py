from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def _slim_rec(r: Dict[str, Any]) -> Dict[str, Any]:
    keys = (
        "player_id",
        "player_name",
        "pos",
        "pos_bucket",
        "school",
        "prospect_score",
        "model_rank",
        "consensus_rank",
        "reach_risk",
        "market_value_score",
        "team_need_score",
        "scheme_fit_score",
        "final_draft_score",
        "leverage_score",
        "availability_at_pick",
        "recommendation_rank",
    )
    return {k: r.get(k) for k in keys}


def build_draft_intel_payload(
    board: Dict[str, Any],
    recommendations: List[Dict[str, Any]],
    simulation: Dict[str, Any],
) -> Dict[str, Any]:
    top = [_slim_rec(dict(x)) for x in (recommendations[:12] if recommendations else [])]
    needs = board.get("team_needs", {}).get("need_scores", {})
    scheme = board.get("team_scheme", {}).get("raw", {})
    epa = board.get("team_needs", {}).get("epa_profile", {})
    return {
        "mode": "draft",
        "team": board.get("team"),
        "combine_season": board.get("combine_season"),
        "eval_season": board.get("eval_season"),
        "pick_number": simulation.get("pick_number"),
        "simulation": {
            "n_simulations": simulation.get("n_simulations"),
            "temperature": simulation.get("temperature"),
        },
        "team_need_scores": needs,
        "team_scheme_summary": scheme,
        "team_epa_z": epa,
        "recommendations": top,
    }


def template_draft_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic draft analyst copy grounded strictly on payload numbers.
    """
    recs = payload.get("recommendations") or []
    team = payload.get("team", "")
    pick = payload.get("pick_number", "")
    needs = payload.get("team_need_scores") or {}
    if not recs:
        return {
            "best_pick_explanation": f"No ranked recommendations available for {team} at pick {pick}.",
            "risk_analysis": "Insufficient board data to assess risk.",
            "alternative_picks": [],
            "if_we_pass": "Passing is undefined without a ranked list.",
            "why_not_other_targets": [],
            "alternate_outcomes": "",
        }
    top = recs[0]
    alt = recs[1:4]
    name = top.get("player_name", "")
    pos = top.get("pos", "")
    final = top.get("final_draft_score", top.get("leverage_score"))
    p_avail = top.get("availability_at_pick")
    need_s = top.get("team_need_score")

    need_sorted = sorted(needs.items(), key=lambda x: -x[1])[:3]
    need_txt = ", ".join(f"{p}:{round(v, 1)}" for p, v in need_sorted)

    best = (
        f"At pick {pick}, the board ranks {name} ({pos}) highest on levered score "
        f"(final model score ~{final}, availability ~{p_avail}). "
        f"Team need at {pos} registers ~{need_s} on a 0–100 scale vs other buckets [{need_txt}]."
    )
    risk = (
        f"Risk profile for {name}: production/efficiency signals are sourced from nflverse "
        f"where available; otherwise combine movement/athletic traits anchor the grade. "
        f"Availability ~{p_avail} implies {'limited' if p_avail and float(p_avail) < 0.35 else 'meaningful'} "
        "chance another club selects this profile before your next slot."
    )
    alts = [f"{r.get('player_name')} ({r.get('pos')}) — score {r.get('final_draft_score')}" for r in alt]
    why_not = []
    for r in alt[:3]:
        nm = r.get("player_name", "")
        rr = r.get("reach_risk")
        cr = r.get("consensus_rank")
        why_not.append(
            f"Not tabbed first: {nm} — levered score {r.get('final_draft_score')} vs {final}; "
            f"reach_risk {rr if rr is not None else 'n/a'} (model_rank−consensus_rank); "
            f"consensus slot ~{cr if cr is not None else 'n/a'}."
        )
    if_we_pass = (
        f"If {team} passes on {name}, the next tier includes: {', '.join(alts) or 'no alternates listed'}. "
        "Monitor simulated availability: a high availability figure suggests the player may remain "
        "reachable, reducing urgency at this exact pick."
    )
    pivot = alt[0].get("player_name") if alt else "next levered name"
    alt_out = (
        "Alternate outcome tree (grounded on availability only): "
        f"if {name} is gone, pivot to {pivot} unless their availability is materially lower "
        "than the simulation snapshot."
    )
    return {
        "best_pick_explanation": best,
        "risk_analysis": risk,
        "alternative_picks": alts,
        "if_we_pass": if_we_pass,
        "why_not_other_targets": why_not,
        "alternate_outcomes": alt_out,
    }


def build_draft_phi4_prompt(payload: Dict[str, Any]) -> str:
    js = json.dumps(payload, ensure_ascii=False)
    return (
        "You are GridironIQ's AI Draft Analyst. Use ONLY the JSON payload below.\n"
        "Do not invent players, medical info, or rumors.\n"
        "Return a single JSON object with keys: "
        "best_pick_explanation, risk_analysis, alternative_picks (array of strings), if_we_pass, "
        "why_not_other_targets (array of strings), alternate_outcomes (string).\n"
        "Write like an NFL front office: concise, decisive, tied to the numbers in the payload.\n\n"
        f"PAYLOAD:\n{js}\n"
    )


def generate_draft_analyst(
    payload: Dict[str, Any],
    ai_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Template or Phi-4 JSON output for the draft analyst panel.
    """
    mode = (ai_mode or "").lower().strip() or None
    resolved = mode if mode in {None, "template", "phi4"} else None

    if resolved == "phi4":
        from .phi4_provider import Phi4Provider  # noqa: PLC0415

        prov = Phi4Provider()
        prompt = build_draft_phi4_prompt(payload)
        try:
            raw = prov._raw_generate(prompt, max_new_tokens=400)  # noqa: SLF001
            text = raw.strip()
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                obj = json.loads(text[start : end + 1])
                if isinstance(obj, dict):
                    return {**obj, "provider": "phi4", "fallback": False}
        except Exception:
            pass

    out = template_draft_analysis(payload)
    out["provider"] = "template"
    out["fallback"] = resolved == "phi4"
    return out
