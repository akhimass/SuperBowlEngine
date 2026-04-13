# AI Statistician – GridironIQ

The AI Statistician is a grounded NFL analytics explainer that turns GridironIQ model outputs into concise, football-native narratives.

It is **not** a generic chatbot: it only uses existing GridironIQ data (matchup results, scouting reports, situational and broadcast reports) and returns a small, structured explanation object.

## Modes

- `template` (default)
  - Deterministic, no model calls.
  - Uses `report_generator` fields to build a concise explanation.
- `phi4` (planned)
  - Will use a local clone of `Phi-4-multimodal-instruct` to generate richer language from the same grounded context.
  - For V1, the code path is stubbed and will always fall back to `template`.

Configure mode via environment:

```bash
export GRIDIRONIQ_AI_MODE=template  # or phi4
export GRIDIRONIQ_PHI4_REPO_PATH="Phi-4-multimodal-instruct"
```

## Data flow

1. Core engines produce:
   - `MatchupResult` (win probability, projected score, keys won, key edges, drivers).
   - Structured scouting report from `report_generator.generate_report`.
   - Situational report from `/api/report/situational`.
   - Broadcast report from `/api/report/broadcast`.
   - Optional QB comparison from `/api/qb/compare`.
2. `ai.explainer.build_explainer_context` bundles this into an `ExplainerContext`.
3. `ai.explainer.generate_ai_explanation` selects a provider (`template` or `phi4`) and returns an `AIExplanationResult`.
4. `report_generator.generate_report` attaches this under `ai_statistician` in the report JSON.
5. Frontend pages (`MatchupAnalysis`, `GameReport`) render the explanation in an **AI Statistician** panel/tab.

## Backend APIs

- `POST /api/ai/explain-matchup`
  - Body:
    ```json
    {
      "season": 2024,
      "team_a": "GB",
      "team_b": "DET",
      "mode": "opp_weighted",
      "ai_mode": "template"
    }
    ```
  - Returns:
    ```json
    {
      "ai_statistician": {
        "summary": "...",
        "top_3_reasons": ["...", "...", "..."],
        "what_matters_most": "...",
        "what_could_flip_it": "...",
        "why_prediction_was_right_or_wrong": null,
        "confidence_note": "..."
      }
    }
    ```

- `GET /api/ai/config`
  - Returns current mode and whether the Phi‑4 repo is visible on disk.

- `GET /api/ai/health`
  - Light health check confirming the template provider works and whether Phi‑4 is discoverable.

## Frontend usage

- `MatchupAnalysis`:
  - Calls `/api/matchup/report` which now includes `ai_statistician` in the payload.
  - Renders an **AI Statistician** tab showing:
    - Summary
    - Top reasons
    - What matters most
    - What could flip it
    - Confidence note

- `GameReport`:
  - Uses the `ai_statistician` field in the historical game report to show:
    - Why the model thought what it did.
    - For historical games, why it was right or wrong (when available).

## Multimodal future

The current integration is text-only and grounded in structured JSON.

Future work:

- Use paths in `visual_references` to pass heatmaps and diagrams into Phi‑4 as image inputs.
- Extend prompts to ask for:
  - Summaries of situational heatmaps.
  - Explanations of field diagrams and matchup charts.

