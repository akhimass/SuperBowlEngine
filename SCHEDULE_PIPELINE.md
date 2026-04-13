## GridironIQ Schedule & Report Pipeline

This document describes how GridironIQ powers season-wide schedule exploration and validation using real nflreadpy/nflverse data for seasons 2020–2025.

### Components

- **Custom Matchup Predictor**
  - Frontend: `gridiron-intel/src/pages/MatchupAnalysis.tsx`
  - Backend:
    - `src/gridironiq/matchup_engine.py` (`run_matchup`)
    - `src/gridironiq/api.py` (`POST /api/matchup/run`, `POST /api/matchup/report`)
  - Supports any valid team pairing and season 2020–2025, with modes:
    - `opp_weighted` (full-season opponent-adjusted)
    - `regular` (regular season only)
    - `postseason` (postseason only)

- **Schedule Explorer**
  - Frontend: `gridiron-intel/src/pages/ScheduleExplorer.tsx`
  - Backend:
    - `src/gridironiq/schedule_engine.py` (`run_schedule_predictions`, `list_schedule`)
    - `src/gridironiq/pipeline_cache.py` (JSON cache)
    - `src/gridironiq/api.py` (`GET /api/schedule`)
  - Shows real NFL games with:
    - home/away teams and final score
    - model-predicted winner, win probability, and projected score
    - correctness badge (Correct / Incorrect / Pending)

- **Game Report**
  - Frontend: `gridiron-intel/src/pages/GameReport.tsx`
  - Backend:
    - `src/gridironiq/schedule_engine.py` (`build_game_report`)
    - `src/gridironiq/api.py` (`GET /api/game-report`)
  - Combines schedule metadata, `run_matchup`, `generate_report`, situational and broadcast reports into a single JSON bundle and renders it with tabs.

- **Precompute / Cache Pipeline**
  - Backend helpers: `src/gridironiq/pipeline_cache.py`
  - Script: `scripts/build_schedule_pipeline.py`
  - Caches:
    - `outputs/schedule_predictions/{season}_{phase}.json`
    - `outputs/schedule_reports/{season}/{game_id}.json`

### Endpoints

- `POST /api/matchup/run`
  - Request: `{ "season": 2024, "team_a": "GB", "team_b": "DET", "mode": "opp_weighted" }`
  - Response: win probability, predicted winner, projected score, key_edges, keys_won, top_drivers, logos.

- `POST /api/matchup/report`
  - Request: same as `/api/matchup/run`
  - Response: full scouting report (`summary`, strengths, profiles, explanation, projected score, keys_won, top drivers, logos).

- `GET /api/schedule?season=2024&phase=all`
  - Uses cached schedule predictions if present, otherwise computes and writes them.
  - Returns `{ season, phase, games: [...] }` where each game has:
    - `game_id, season, week, season_type`
    - `home_team, away_team, home_score, away_score`
    - `predicted_winner, predicted_score, win_probability, correct`.

- `GET /api/game-report?season=2024&game_id=2024_01_GB_DET`
  - Uses cached game report if present, otherwise computes and writes it.
  - Returns full report bundle for a single historical game.

- `POST /api/schedule/build`
  - Body: `{ "season": 2024, "phase": "all", "build_reports": true }`
  - Runs season-wide prediction and, optionally, full report generation.
  - Summary response: `{ season, phase, games_processed, reports_built }`.

### Precompute Script

Run the script to build schedule predictions and reports for a season:

```bash
cd /Users/akhichappidi/SuperBowlEngine

uv run python scripts/build_schedule_pipeline.py --season 2024 --phase all --build-reports
```

This will:

- Compute predictions for all completed games in the specified season/phase.
- Optionally build full reports for each game.
- Write JSON cache files under `outputs/schedule_predictions/` and `outputs/schedule_reports/`.

### Supported Seasons

- The current pipeline is designed for seasons **2020–2025**, assuming nflreadpy/nflverse has data for those years.

### Flows

- **Free-form matchup prediction**
  - Use the Matchup Predictor page (`/matchup`) to select any season (2020–2025) and any two different teams.
  - Backend runs `run_matchup` + `generate_report` on-demand; no schedule context is required.

- **Historical result validation**
  - Use the Schedule Explorer (`/schedule`) to browse real games by season and phase.
  - Each card shows model prediction vs actual result.
  - Click a card to open the Game Report page (`/schedule/:season/:gameId`) with full reports and comparison.

