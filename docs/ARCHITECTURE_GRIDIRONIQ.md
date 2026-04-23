## GridironIQ Architecture Plan

This document outlines how the existing projects in this repo come together into a single NFL matchup intelligence platform: **GridironIQ**.

The goal is to move toward a **Python analytics backend + Lovable frontend** as the long‑term source of truth, while treating the R report engine as a migration source during the transition.

---

## 1. Current Assets (Repo Audit)

### 1.1 Lovable Frontend – `gridiron-intel/`

**Tech stack**

- Vite + React + TypeScript
- TailwindCSS + shadcn‑ui components
- React Router, TanStack Query

**Key entry points**

- `src/App.tsx` – wraps the app in `QueryClientProvider` and `BrowserRouter`.
- Routes:
  - `/` → `pages/Index.tsx` (landing / overview).
  - `/matchup` → `pages/MatchupAnalysis.tsx`.
  - `/backtest` → `pages/Backtesting.tsx`.
  - `/reports` → `pages/ReportLibrary.tsx`.
  - fallback → `pages/NotFound.tsx`.
- `README.md` – project overview and usage instructions.

**What it already supports conceptually**

- A **landing page** shell.
- Dedicated pages for:
  - Matchup analysis.
  - Backtesting.
  - Report library.
- Modern component stack (to plug real APIs into).

At the moment, the frontend is mostly scaffolded UI; it expects to talk to an API but is not yet wired to a real analytics backend.

---

### 1.2 Legacy R Report Engine (removed)

This repo previously contained a Shiny-based report engine under `NFL_Report_Engine/` that produced matchup heatmaps, broadcast-style reports, and detailed situational tables for the 2024 season. All of that functionality has now been reimplemented in Python (`src/gridironiq/reports/`) and selected example PNGs have been migrated into `outputs/legacy_reports/` and `gridiron-intel/public/reports/` for design and portfolio reference. The R project directory has been removed from version control; there is no remaining runtime dependency on R.

---

### 1.3 Python Modeling / Backend – `src/superbowlengine/` and `scripts/`

This is the current Python analytics engine originally built as **SuperBowlEngine**.

**Key modules**

- `models/professor_keys.py`
  - **Team Outcome Engine** based on the 5 Keys:
    - Time of Possession (TOP).
    - Turnovers.
    - Big Plays.
    - 3rd Down %.
    - Red Zone TD %.
  - Implements the **“3 keys wins” rule** as a logistic‐style predictor.
  - Produces:
    - Predicted winner.
    - Win probabilities `p_team_a_win`, `p_team_b_win`.
    - Keys won per team.
    - Top 3 drivers / contributions.
    - Explanation object (key winners, margins, contributions, logit).
- `models/score_model.py`
  - Regresses key margins (plus SOS) to:
    - Predicted margin.
    - Predicted total.
    - Implied score for each team.
  - Outputs score confidence intervals (margin/total SDs).
- `qb/production.py`, `qb/model.py`, `qb/validate.py`
  - **QB Production Engine**:
    - Drive sustainability, situational execution, off‑script value.
    - Defense‑adjusted via opponent strength (REG EPA/success).
  - `qb_prod_card.py` in `viz/` renders a compact production strip for two QBs.
- `features/keys.py`, `features/keys_pipeline.py`, `features/opponent_weights.py`
  - Compute team keys from PBP.
  - Support aggregation modes: aggregate, per_game, opp_weighted.
  - Implement **opponent strength** weights and turnover‑outlier dampener.
- `features/sos.py`, `analysis/rank_keys.py`
  - Build strength of schedule (SOS) and ranking/percentile views.
- `data/load.py`, `data/availability.py`, `data/games.py`, `data/errors.py`
  - Load PBP and schedules via **nflreadpy**.
  - Provide **availability** / readiness assessment (GREEN/YELLOW/RED).

**Key scripts**

- `scripts/run_and_make_slide5.py`
  - End‑to‑end pipeline to:
    - Load PBP (REG + POST) via nflreadpy.
    - Compute TeamKeys for matchup teams.
    - Build contexts (SOS, expected turnovers, etc.).
    - Call the Professor Keys engine for win probability and explanation.
    - Call the score model for projected margin and total (for display).
    - Render slide‑ready visuals:
      - `outputs/slide5_prediction.png`
      - `outputs/slide5_explainer.png`
    - Write `outputs/prediction.json` (as seen currently in this repo).
- `scripts/make_qb_prod_card.py`
  - Uses QB production components and scores to render:
    - `outputs/qb_prod_card.png` (two‑QB production strip).
    - `outputs/qb_prod_report_*.json` (per‑QB production details).
- Other useful utilities:
  - `scripts/list_team_games.py` – inspect team schedules/games.
  - `scripts/inspect_nflreadpy_columns.py` – inspect PBP column availability.

**Current Python outputs already in use**

- **Win probability and explanation** for a given matchup (e.g., Super Bowl LX).
- **Score projection** (margin, total, implied score).
- **Scouting‑style visuals**:
  - Team outcome slide (`slide5_prediction.png` + `slide5_explainer.png`).
  - QB production card (`qb_prod_card.png`).
- JSON outputs for:
  - Matchup prediction (`prediction.json`).
  - QB production reports (`qb_prod_report_*.json`).

---

## 2. Target Architecture (GridironIQ)

High‑level goal: turn this repo into a coherent **NFL matchup intelligence platform** with:

- **Lovable frontend UI** as the main product shell.
- **Python backend** as the analytics and API source of truth.

### 2.1 Target Directory Layout

Target structure (evolutionary, not all at once):

- `gridiron-intel/` – frontend app (Lovable UI, main product shell).
- `src/gridironiq/` (or `backend/`) – Python analytics backend and FastAPI app.
- `data/` or `supabase/` – future persistent data / API payload storage.
- `outputs/` – generated scouting reports, prediction JSON, matchup visuals.
- `src/superbowlengine/` – original SuperBowlEngine module, gradually refactored/aliased into `gridironiq` backend.

Over time, the **Python backend** becomes the single source of truth for:

- Win probabilities.
- Score projections.
- Team matchup explanations.
- QB production metrics.
- Backtests and calibration.

The frontend consumes **only API responses**, not R or Python internals directly.

---

## 3. Migration Path: R → Python (completed)

All major concepts from the former R engine have been ported into Python-native modules under `src/gridironiq/reports/`. R is no longer used at runtime; remaining R-era PNGs live only as static examples under `outputs/legacy_reports/` and `gridiron-intel/public/reports/`.

### 3.1 Port Concepts, Not Code

In Python, prioritize:

- Situational buckets: down/distance, field position.
- Tendencies: run/pass mix, success rates, explosive rates by bucket.
- Heatmap‑style metrics, but rendered via Python plotting libraries or frontend charts.
- Broadcast‑style “what matters” summaries.

The goal (now achieved) was to build **Python‑native** equivalents of:

- Matchup graphics (offense vs defense).
- Heatmaps (tendencies, success ranks).
- Broadcast/presentation reports.

Once Python implementations are stable and cover the main use cases, R becomes optional and then removable.

### 3.2 Long‑Term: Decommission R

- The `NFL_Report_Engine/` directory has been removed from the repo.
- There is no runtime dependency on R; all reporting flows are Python-native.
- Only documentation and a curated set of static PNG outputs are kept as design reference.

---

## 4. Frontend / Backend Integration Plan

### 4.1 Backend Responsibilities (Target: `src/gridironiq/`)

Create a new backend package (name: `gridironiq`) that:

- Wraps existing SuperBowlEngine logic into more general modules:
  - `matchup_engine.py`
    - Single entry point for any NFL matchup (REG/POST).
    - Inputs: season, week or postseason round, team_a, team_b, mode (`regular`, `postseason`, `opp_weighted`).
    - Outputs:
      - Win probabilities.
      - Projected score.
      - Key edges and top drivers.
      - Explainability object.
  - `offense_features.py`
    - Derive offensive metrics per team/game:
      - Points per drive, EPA/play, success rate, early down success, explosive play rate, 3rd down %, red zone TD %, sack rate allowed.
  - `defense_features.py`
    - Mirror for defense:
      - Points per drive allowed, EPA/play allowed, defensive success rate allowed, explosive plays allowed, 3rd down % allowed, red zone TD % allowed, sack/pressure proxies.
  - `situational_features.py`
    - Opponent‑adjusted strength, recent form, home/away, postseason weighting, turnover volatility adjustments.
  - `qb_production_engine.py`
    - Reuse/refine existing QB production logic (drive sustain, situational, off‑script, defense‑adjusted) in a gridiron‑agnostic namespace.
  - `report_generator.py`
    - Build **scouting‑style JSON**:
      - Summary paragraph.
      - Team A / Team B strengths.
      - Offensive and defensive profiles.
      - QB impact section.
      - Final prediction with confidence/caution notes.
  - `backtest_engine.py`
    - Run historical matchups and compare:
      - Predicted vs actual winner.
      - Projected vs actual score.
      - Win‑probability calibration.
      - Margin error.
    - Output JSON/CSV suitable for frontend charts.

- Expose a **FastAPI** application:
  - `GET /api/teams`
  - `POST /api/matchup/run`
  - `POST /api/matchup/report`
  - `POST /api/backtest/run`
  - `GET /api/reports`
  - `POST /api/qb/compare`

Each endpoint returns frontend‑friendly JSON objects with:

- Team metrics.
- Matchup metrics.
- Prediction and projections.
- Top drivers and key edges.
- Links (paths) to generated visual assets in `outputs/` where applicable.

### 4.2 Frontend Responsibilities – `gridiron-intel/`

Use the existing Lovable scaffold and connect it to the FastAPI backend:

- **Landing page (`/`)** – present GridironIQ as:
  - “NFL matchup intelligence platform.”
  - Highlight modules: matchup engine, scouting reports, QB production, backtests.
- **Matchup page (`/matchup`)** – call `/api/matchup/run` and `/api/matchup/report`:
  - Inputs: season, week/round, teams, mode.
  - Outputs:
    - Win probability.
    - Projected score.
    - Key edges and drivers.
    - Offense/defense comparison.
    - QB comparison strip.
    - Scouting report sections ready for cards/tables.
- **Backtesting page (`/backtest`)** – call `/api/backtest/run`:
  - Show calibration charts, margin errors, win‑prob vs actual results.
- **Report library (`/reports`)** – call `/api/reports`:
  - Browse saved matchup runs and scouting reports by team / season / week.
- **QB comparison view** – likely a sub‑route or component that calls `/api/qb/compare`:
  - Compact production strips with explainability notes.

The frontend should **not** compute metrics; it should:

- Call the backend.
- Render cards, tables, and visuals.
- Provide filters and controls.

---

## 5. Short‑Term vs Long‑Term Responsibilities

### 5.1 Short‑Term

- `gridiron-intel/`
  - Keep existing routes/pages.
  - Ensure all data flows use real backend APIs (no local mocks).
  - Focus on:
    - Matchup page skeleton.
    - Simple backtest and report list views.
- `src/superbowlengine/`
  - Remains the **working analytics engine**.
  - Continue using:
    - `scripts/run_and_make_slide5.py` for manual runs.
    - `scripts/make_qb_prod_card.py` for QB production visuals.
  - Begin extracting reusable pieces into `gridironiq` modules without breaking existing scripts.
- `NFL_Report_Engine/`
  - Left intact as a **reference** and optional manual report generator.
  - No refactors; only documentation and selective script calls via experimental bridges.

### 5.2 Long‑Term

- `src/gridironiq/` (or `backend/`)
  - Becomes the canonical analytics and API layer.
  - Hosts all generalized engines:
    - Matchup.
    - Offense/defense features.
    - Situational context.
    - QB production.
    - Backtesting.
    - Report generation.
  - SuperBowlEngine code is either:
    - Moved here.
    - Or wrapped and then deprecated.
- `gridiron-intel/`
  - Fully wired to FastAPI.
  - Provides production‑ready UI experiences:
    - Matchup intelligence.
    - Scouting reports.
    - QB comparisons.
    - Historical backtests.
- `NFL_Report_Engine/`
  - Archived but preserved for:
    - Design inspiration.
    - Historical comparison.
- `data/` / `supabase/`
  - Houses schemas and integration code for:
    - Teams, games, matchup_runs, scouting_reports, qb_reports, backtest_runs.
  - Backed by Supabase or another database when ready.

---

## 6. Concrete Next Steps (Implementation Roadmap)

The following steps continue from this architecture, in roughly this order:

1. **Confirm naming and backend package location.**  
   - Create `src/gridironiq/` as the new backend package root (keeping `src/superbowlengine/` intact for now).

2. **Introduce generalized matchup engine API (Python‑side only).**  
   - Add `src/gridironiq/matchup_engine.py` that wraps existing SuperBowlEngine logic for:
     - Inputs: season, week/round, team_a, team_b, mode.
     - Outputs: structured `MatchupResult` dataclass.
   - Internally reuse:
     - `superbowlengine.features.*` for keys and SOS.
     - `superbowlengine.models.*` for win prob and score projections.

3. **Carve out feature modules.**  
   - Add stubs for:
     - `src/gridironiq/offense_features.py`
     - `src/gridironiq/defense_features.py`
     - `src/gridironiq/situational_features.py`
   - Initially, these can call into existing features and return structured dicts / dataclasses.

4. **Wrap QB production into `gridironiq.qb_production_engine`.**  
   - Create `src/gridironiq/qb_production_engine.py` that:
     - Uses `superbowlengine.qb.production` and `superbowlengine.qb.model` under the hood.
     - Exposes a clean, gridironiq‑branded API that returns QB production cards and JSON‑ready summaries.

5. **Define report JSON contracts.**  
   - Add `src/gridironiq/report_generator.py` that:
     - Takes outputs from matchup, features, and QB engines.
     - Returns a single scouting‑style JSON payload shaped for the frontend.

6. **Add backtesting skeleton.**  
   - Add `src/gridironiq/backtest_engine.py` that:
     - Can iterate over historical games and call `matchup_engine`.
     - Outputs CSV/JSON for calibration and accuracy charts.

7. **Stand up FastAPI app.**  
   - Add `src/gridironiq/api.py` (or `main.py`) with endpoints:
     - `/api/teams`, `/api/matchup/run`, `/api/matchup/report`, `/api/backtest/run`, `/api/reports`, `/api/qb/compare`.
   - Initially, wire only `/api/matchup/run` and `/api/qb/compare` using the new engines.

8. **Connect the Lovable frontend to FastAPI.**  
   - In `gridiron-intel/`:
     - Replace mock data in `MatchupAnalysis`, `Backtesting`, and `ReportLibrary` with real API calls.
     - Ensure environment configuration for backend URL.

9. **Document R → Python migration plan.**  
   - Add `MIGRATION_R_TO_PYTHON.md` to:
     - Detail current R capabilities.
     - Map R features to Python modules.
     - Track what has been ported vs what remains.

10. **Design future schemas.**  
    - Create `SCHEMA_PLAN.md` describing tables/entities for:
      - teams, games, matchup_runs, scouting_reports, qb_reports, backtest_runs.
    - Align JSON contracts in the API with these future schemas.

All of these steps preserve existing scripts and the R engine while moving toward a unified GridironIQ backend and frontend.\n*** End Patch"} -->
