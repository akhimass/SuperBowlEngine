## GridironIQ v2 model training (2020–2025)

### Overview

GridironIQ v2 uses a multi-layer modeling stack:

1. **Win probability model** (classification)
2. **Margin model** (regression)
3. **Total points model** (regression)
4. **5 Keys** (explainability layer only; not the predictive backbone)

### Leakage control (critical)

Training rows are constructed per historical game using **pregame-style features**:

- For a game at week \(w\), feature calculations only use plays from **weeks < w** in the same season.
- Week 1 games are skipped (no prior data).
- Postseason rows use all regular-season data plus earlier postseason games if a usable ordering exists.

Implementation: `src/gridironiq/models/training_data.py`.

### Features used

Stable matchup differentials:

- `epa_edge`
- `success_edge`
- `explosive_edge`
- `early_down_success_edge`
- `third_down_edge`
- `redzone_edge`
- `sack_edge`
- `sos_edge`
- `recent_epa_edge`

### Targets

- `win_target`: 1 if home team won else 0
- `margin_target`: `home_score - away_score`
- `total_target`: `home_score + away_score`

### Artifacts (saved)

Saved under `outputs/model_artifacts/`:

- `win_prob_model.json`
- `margin_model.json`
- `total_model.json`

### Training script

Run:

```bash
uv run python scripts/train_and_evaluate_models.py --start 2020 --end 2025
```

This will:
- build training rows
- fit all models
- save artifacts
- print evaluation metrics

### Live integration

The live predictor loads artifacts from:

- `outputs/model_artifacts/`

Or a custom directory via:

- `GRIDIRONIQ_MODEL_ARTIFACT_DIR=/path/to/dir`

Fallback behavior:
- if artifacts are missing, the models use conservative defaults.

