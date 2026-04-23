## AI Statistician – Phi-4 Integration Verification

### Environment

From repo root:

```bash
cd /Users/akhichappidi/SuperBowlEngine

export GRIDIRONIQ_AI_MODE=phi4
export GRIDIRONIQ_PHI4_REPO_PATH="Phi-4-multimodal-instruct"
# Optional if model weights live in a different folder or HF cache:
# export GRIDIRONIQ_PHI4_MODEL_PATH="Phi-4-multimodal-instruct"
# Optional device preference:
# export GRIDIRONIQ_PHI4_DEVICE=auto  # or cpu|cuda

uv run uvicorn gridironiq.api:app --reload --host 0.0.0.0 --port 8001
```

### Backend status endpoints

- `GET /api/ai/config`
  - Returns:
    - `mode`: value of `GRIDIRONIQ_AI_MODE` (e.g. `"phi4"`).
    - `phi4_repo_path`: resolved repo path.
    - `phi4_model_path`: resolved model path.
    - `phi4_available`: `true` if model path exists.
    - `phi4_loaded`: `true` after first successful model load.
    - `multimodal_enabled`: `false` (text-only V1).
    - `fallback_active`: `true` when template is used instead of Phi-4.

- `GET /api/ai/health`
  - Returns:
    - `template_ok`: whether the template provider works.
    - `phi4_repo_path`, `phi4_model_path`.
    - `phi4_available`, `phi4_loaded`, `multimodal_enabled`.
    - `phi4_smoke_ok`: whether a minimal Phi-4 invocation succeeded.

### Functional test

1. **Matchup explanation**

```bash
curl -X POST "http://127.0.0.1:8001/api/ai/explain-matchup" \
  -H "Content-Type: application/json" \
  -d '{"season": 2024, "team_a": "GB", "team_b": "DET", "mode": "opp_weighted"}'
```

Expect:

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

2. **Frontend**

```bash
cd /Users/akhichappidi/SuperBowlEngine/gridiron-intel

export VITE_API_BASE_URL="http://127.0.0.1:8001"
export VITE_AI_MODE="phi4"

npm run dev
```

Then:

- On `/matchup`:
  - Run a matchup and open the **AI Statistician** tab.
  - The panel shows the provider badge (Phi-4 or Template) and structured explanation.

- On `/schedule/:season/:gameId`:
  - Check the **AI Statistician** tab on the Game Report page for a historical explanation.

### Multimodal status

- **Current**: text-only, grounded in JSON report data.
- **Next**:
  - Extend `ExplainerContext.visuals` with PNG paths.
  - Update `Phi4Provider` to pass images into Phi-4 when stable multimodal helpers are available.

