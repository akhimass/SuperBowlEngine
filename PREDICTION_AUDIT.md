## Prediction Pipeline Audit

### Current GridironIQ pipeline

1. **Input (season, team_a, team_b, mode)**  
   - Frontend calls `POST /api/matchup/run` with `{ season, team_a, team_b, mode }`.

2. **Backend wrapper: `gridironiq.matchup_engine.run_matchup`**
   - Loads PBP and schedules via `superbowlengine.data.get_pbp` / `get_schedules`.
   - Selects PBP subset based on mode (`regular`, `postseason`, `opp_weighted`).
   - Computes `TeamKeys` for both teams via `prepare_keys_for_matchup`.
   - Computes simple SOS context from regular-season game results.
   - Calls `superbowlengine.models.professor_keys.predict` to get:
     - `p_team_a_win`, `p_team_b_win`.
     - `predicted_winner`.
     - `keys_won`, `key_winners`, `margin_table`, `driver_ranking`.
   - Calls `superbowlengine.models.score_model.predict_score` to get:
     - `predicted_margin` (point differential).
     - `predicted_total` (total points).
     - `predicted_score` (team_a → A score, team_b → B score).
     - `score_ci` (margin_sd, total_sd).
   - Returns a `MatchupResult` with:
     - `win_probability` (p_team_a_win).
     - `predicted_winner`.
     - `projected_score` (from `predict_score`).
     - `keys_won`, `key_edges`, `top_drivers`, `explanation`.

3. **API: `POST /api/matchup/run`**
   - Serializes `MatchupResult` to JSON, enriches with team logos.

4. **Frontend mapping (`gridiron-intel/src/lib/api.ts → runMatchup`)**
   - Maps `win_probability` (0–1) → `%` for UI.
   - Reads `projected_score[teamA]` / `projected_score[teamB]` into `MatchupResult.projectedScoreA/B` for display.

### Original SuperBowlEngine score model

- `src/superbowlengine/models/score_model.py`:
  - `predict_score`:
    - Uses fixed `ScoreModelArtifacts` (trained Ridge regression on POST games) to map 5 Keys + SOS margins → margin & total.
    - Reconstructs scores via:
      - `A = (total + margin) / 2`, `B = (total - margin) / 2`.
      - Rounds and clamps at 0.
    - Default/artifacts path:
      - If no artifacts, returns conservative default: margin 0, total 45, scores ~22–23.

### Differences / drift points

- GridironIQ uses the same `predict_score` function and default artifacts loader as the original engine.
- Path for potential drift:
  - Updated training artifacts (if `outputs/score_model.json` was regenerated with different data).
  - Different mode (`opp_weighted` vs original specific playoff-only keys) producing more extreme margins.
  - No additional realism clamps on `pred_margin` / `pred_total` before reconstructing scores.

