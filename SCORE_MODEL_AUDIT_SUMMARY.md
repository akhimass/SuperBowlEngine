## Score Model Audit Summary

### Root cause(s)

- GridironIQ uses the same `predict_score` function as the original SuperBowlEngine, but:
  - The Ridge regression artifacts can produce large `predicted_margin` and `predicted_total` values for some extreme 5 Keys margins.
  - There were **no realism clamps** on those raw outputs before reconstructing team scores, so:
    - Very large margin + total combinations could yield scores such as 47–0 or 77–0.

### Fixes implemented

- **Backend: `src/superbowlengine/models/score_model.py`**
  - Added realism guards in `predict_score`:
    - Store raw values:
      - `unclamped_margin = float(pred_margin)`
      - `unclamped_total = float(pred_total)`
    - Clamp:
      - `pred_total` to `[24.0, 62.0]` (plausible NFL totals).
      - `pred_margin` to `[-24.0, 24.0]` (up to ~3–4 scores).
    - Recompute implied scores from clamped margin/total:
      - `A = (total + margin) / 2`, `B = (total - margin) / 2`, then round and clamp to `>= 0`.
    - Attach debug info to `score_ci`:
      - `unclamped_margin`, `unclamped_total`, and `score_clamped: bool`.

- **Audit scripts**
  - `scripts/audit_predictor_consistency.py`
    - Compares original SuperBowlEngine predictor vs current `gridironiq.matchup_engine.run_matchup` for any matchup.
  - `scripts/audit_score_distribution.py`
    - Runs the score model across a season, prints:
      - Mean/min/max total and margin,
      - Min/max team scores,
      - Count of games where clamping was applied.

- **Tests**
  - `tests/test_score_model_realism.py`
    - Ensures:
      - Scores are never negative.
      - Totals land in `[24, 62]`.
      - Margins land in `[-24, 24]` for a representative feature set.

### Alignment with original SuperBowlEngine

- Win probability and winner selection:
  - Still driven by `superbowlengine.models.professor_keys.predict` (unchanged).
  - Score projection is a secondary, calibrated display layer and **does not** feed back into winner selection.
- Score behavior:
  - Now constrained to plausible NFL ranges while still reflecting the direction and magnitude implied by 5 Keys and SOS.

