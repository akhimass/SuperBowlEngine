# AI Statistician – Phi-4 Integration Plan

## Repo location

- Local Phi-4 repo cloned into this workspace at:
  - `Phi-4-multimodal-instruct/` (sibling of `src/` and `gridiron-intel/`).
- Upstream model card: `https://huggingface.co/microsoft/Phi-4-multimodal-instruct`.

## High-level strategy

- GridironIQ will expose a dedicated **AI Statistician** layer that:
  - Is always grounded in **existing GridironIQ outputs**:
    - `MatchupResult` from `matchup_engine.run_matchup`.
    - JSON scouting report from `report_generator.generate_report`.
    - Situational and broadcast reports from `reports/matchup_report.py` and `reports/broadcast_report.py`.
    - Optional QB comparison from `qb_production_engine`.
    - Optional references to generated visuals (heatmaps, charts).
  - Produces a **structured explanation object**:
    - `summary`
    - `top_3_reasons`
    - `what_matters_most`
    - `what_could_flip_it`
    - `why_prediction_was_right_or_wrong` (for historical games)
    - `confidence_note`
  - Supports two modes:
    - `template` – deterministic, no model calls (safe fallback, unit-testable).
    - `phi4` – uses local Phi‑4‑multimodal‑instruct for richer language.

## Call model vs template

- **Default**: template provider (`GRIDIRONIQ_AI_MODE=template` or unset).
- If `GRIDIRONIQ_AI_MODE=phi4` AND `GRIDIRONIQ_PHI4_REPO_PATH` points to a valid repo:
  - Try to import/use a small local Phi‑4 wrapper.
  - On any failure (import, load, inference), log and **fall back to template** for that request.

## Inputs passed to the AI Statistician

We define an `ExplainerContext` (see `src/gridironiq/ai/schemas.py`) containing:

- `matchup`:
  - `team_a`, `team_b`, `season`, `mode`
  - `win_probability`, `predicted_winner`, `projected_score`
  - `keys_won`, `key_edges`, `top_drivers`
- `scouting_report`:
  - `summary`, `team_a_strengths`, `team_b_strengths`
  - `offensive_profile`, `defensive_profile`
  - `prediction_explanation`, `confidence_notes`
  - richer sections like `executive_summary`, `risk_factors`, `final_prediction_logic`
- `situational` (optional):
  - from `/api/report/situational` – situational_edges + offense_vs_defense.
- `broadcast` (optional):
  - from `build_broadcast_report` – headline, summary, storylines, talking_points.
- `qb_report` (optional):
  - from `qb_production_engine` – sustain/situational/offscript/total scores.
- `visuals` (optional, for future multimodal):
  - paths to PNG heatmaps / field diagrams / matchup charts under `outputs/`.

All numerics, labels, and structures come **directly** from GridironIQ; the AI is not allowed to invent stats.

## Outputs expected from providers

`AIExplanationResult`:

- `summary: str` – 2–3 sentences explaining the matchup overall.
- `top_3_reasons: list[str]` – bullets like “Red Zone TD % edge for PHI (+72.6)”.
- `what_matters_most: str` – single focused concept (“sustained drives and red zone TDs”).
- `what_could_flip_it: str` – how the underdog could flip the game (“win turnover margin by 2+ and finish red zone trips”).
- `why_prediction_was_right_or_wrong: Optional[str]` – only filled for historical games (Schedule/Game Report).
- `confidence_note: Optional[str]` – model confidence and caveats.

## Inference entrypoint

For **V1**, we treat Phi‑4 as a local text-only model invoked via a simple wrapper:

- A `phi4_provider.py` will:
  - Read `GRIDIRONIQ_PHI4_REPO_PATH` (default: `Phi-4-multimodal-instruct`).
  - Lazily import or call a small `generate()` helper (to be implemented inside that repo or via transformers).
  - Build a **single text prompt** using:
    - `prompts.build_system_prompt()`
    - `prompts.build_user_prompt(context)`
  - Request a **JSON-shaped answer** that matches `AIExplanationResult`.
  - Parse that JSON, validate fields, and return `AIExplanationResult`.
- For now, **no direct image input is required**; we just mention image paths in text.

Multimodal support (images) is **Phase 2**:

- When stable, we will:
  - Pass image tensors or file paths down to Phi‑4.
  - Extend prompts to include specific visual tasks (“Summarize this red-zone heatmap in football terms.”).

## Where GridironIQ will call the AI Statistician

- **Backend core:**
  - In `report_generator.generate_report`:
    - After building the structured report, call `ai.explainer.generate_ai_explanation(context, mode)` and attach `ai_statistician` to the JSON.
  - In `schedule_engine.build_game_report`:
    - The embedded `scouting_report` already includes `ai_statistician` (reused).
- **Backend API endpoints:**
  - `POST /api/ai/explain-matchup`:
    - Runs matchup + report + AI explainer and returns only `ai_statistician`.
  - `GET /api/ai/config`:
    - Returns `{ "mode": "...", "phi4_available": bool, "fallback_active": bool }`.
  - `GET /api/ai/health`:
    - Simple readiness check; when `phi4` mode is requested, tries a minimal init and reports status.

## Frontend usage

- **MatchupAnalysis.tsx:**
  - Adds an “AI Statistician” tab/panel.
  - Uses `scoutingReport.ai_statistician` when available.
  - Alternatively, can call `/api/ai/explain-matchup` directly with `ai_mode` when we want on-demand recomputation.

- **GameReport.tsx:**
  - Renders the `ai_statistician` section from the backend game report:
    - For historical games, shows “why the model was right/wrong” and key reasons.

## Mode & configuration

- Environment variables:
  - `GRIDIRONIQ_AI_MODE` – `"template"` (default) or `"phi4"`.
  - `GRIDIRONIQ_PHI4_REPO_PATH` – path to the local repo (default: `Phi-4-multimodal-instruct`).
- Safety:
  - If `GRIDIRONIQ_AI_MODE=phi4` but the repo is missing or inference fails, we:
    - Log clearly at `WARNING` or `ERROR`.
    - Use `TemplateProvider` for that request.
    - Do **not** crash the app.

