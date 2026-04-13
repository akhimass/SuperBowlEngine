# GridironIQ

**GridironIQ** is a full-stack NFL intelligence application: a **React** web app plus a **Python** analytics engine and **FastAPI** backend. It combines explainable game prediction (five-keys framework), schedule and matchup reports, **draft intelligence** (nflverse-backed board, Monte Carlo availability, PDF war room reports), and a **2026 Round 1 mock draft simulator** that runs entirely in the browser with static big-board data and need-aware pick logic.

The repository is a **monorepo**:

| Path | Role |
|------|------|
| **`gridiron-intel/`** | Production UI (Vite, React, TypeScript, shadcn/ui): matchup engine, schedule explorer, draft room, mock draft simulator, report library, backtesting views. |
| **`src/gridironiq/`** | Backend package: FastAPI (`api.py`), matchup and QB engines, schedule pipelines, draft board + team needs, PDF report renderer (Jinja2 + WeasyPrint), optional local Phi-4 text for narratives. |
| **`src/superbowlengine/`** | Original **5 Keys** prediction core, data loaders, features, and professor-style models used by the stack (package name unchanged on PyPI/local install). |
| **`scripts/`** | Training, audits, schedule/report pipelines, logo manifest, backend runner. |
| **`tests/`** | Pytest coverage for models, API payloads, draft engine, reports, AI guardrails, and more. |
| **`docs/`** | Architecture notes, AI statistician, team logos, legacy example assets. |

---

## Features

### Web app (`gridiron-intel`)

- **Matchup Engine** — Pick season and teams; view win probability, keys, and structured scouting context (calls GridironIQ API).
- **Schedule history & game reports** — Browse schedules and per-game narrative-style reports.
- **Draft Room** — Live draft board from the API: team needs, prospect table, recommendations, trade scan, analyst template/AI hooks.
- **2026 Mock Draft** — **Round 1 only** (32 picks): choose your team, make your pick on the clock, AI-style projections for other teams using published 2026 board data and team needs. No network calls; state lives in the session. Route: `/draft/simulator`.
- **Report library & data accuracy** — Report browsing and backtesting-oriented UI tied to backend capabilities.

### Backend (`gridironiq`)

- REST API for matchups, QB comparison, schedule predictions, draft simulate/recommend/intelligence, AI chat guardrails, and **draft PDF reports** (`POST /api/draft/report`).
- **Draft pipeline** — `python -m gridironiq.draft.pipeline` for JSON board output and optional PDFs under `outputs/reports/draft/` (served as static assets when configured).
- **Reports** — Matchup, broadcast, presentation, situational, and heatmap-oriented report builders for JSON (+ optional PNG paths).

### Optional local AI

- **Phi-4** (local weights via `transformers`) can power draft report narratives and explainer flows when configured; **`--no-ai`** or API flags use deterministic templates. No cloud API key is required for core functionality.

---

## Quickstart

### Prerequisites

- **Python** 3.10+ ([uv](https://github.com/astral-sh/uv) or `pip`)
- **Node.js** 18+ for the frontend

### Install Python package

From the repository root:

```bash
uv sync
# or: pip install -e .
```

The installable distribution is still named **`superbowlengine`** in `pyproject.toml` (legacy package name); imports use **`gridironiq`** for the app API and **`superbowlengine`** for the keys engine.

### Run the API

```bash
uv run uvicorn gridironiq.api:app --reload --host 0.0.0.0 --port 8000
```

### Run the web UI

```bash
cd gridiron-intel && npm install && npm run dev
```

Point the UI at your API (e.g. in `.env` or env):

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Open the dev server URL (typically `http://localhost:5173`). Use **Draft Room** for API-backed analysis and **2026 Mock Draft** for the standalone Round 1 simulator.

### Deploy the web app (Vercel)

1. Create a Vercel project from this repo and set **Root Directory** to **`gridiron-intel`**.
2. Add **`VITE_API_BASE_URL`** in Vercel → Environment Variables (Production and Preview), pointing at your public API (no trailing slash), e.g. `https://your-api.example.com`.
3. Deploy. `vercel.json` in `gridiron-intel` runs `npm run build` and rewrites client routes to `index.html` for React Router.

The API must allow your frontend origin. By default, **`https://*.vercel.app`** is allowed via CORS regex. For a custom domain, set **`GRIDIRONIQ_CORS_ORIGINS`** on the API server (see **`.env.example`**). The Python API is not run on Vercel in this setup—host it on Render, Fly.io, Railway, etc.

See **`gridiron-intel/README.md`** for a short checklist.

### NFL data cache (optional)

```bash
export NFLREADPY_CACHE=filesystem
export NFLREADPY_CACHE_DIR=~/.cache/nflreadpy
```

---

## Draft PDF reports (WeasyPrint)

Generate front-office style PDFs from the CLI:

```bash
uv run python -m gridironiq.draft.pipeline \
  --team CAR \
  --season 2025 \
  --picks 19 51 83 \
  --top-n 10 \
  --report \
  --report-type all \
  --no-ai \
  --report-output-dir outputs/reports/draft/
```

**WeasyPrint** needs OS libraries (e.g. **macOS:** `brew install pango`; **Ubuntu:** Pango/Cairo packages per [WeasyPrint docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html)).

| `--report-type` | Output |
|-------------------|--------|
| `needs` | Team need summary |
| `prospect` | Single prospect card (`--prospect "Name"` required) |
| `board` | Multi-page board |
| `all` | All of the above |

---

## API highlights

| Area | Examples |
|------|----------|
| Matchup | `POST /api/matchup/run`, `POST /api/matchup/report`, `POST /api/report/matchup` |
| Schedule | Schedule list, game reports, prediction helpers |
| Draft | `POST /api/draft/simulate`, `recommend`, `intelligence`, **`POST /api/draft/report`** |
| Reports | Broadcast, presentation, situational, heatmap-related payloads |

Static report assets can be mounted at **`/report-assets`** from `outputs/reports/` when running the API.

---

## Team logos

Logo PNGs live in **`teamlogo/`** and are mirrored under **`gridiron-intel/public/teamlogo/`** for the UI. Regenerate the manifest with:

```bash
python scripts/generate_team_logo_manifest.py
```

Sync copies into the frontend when needed:

```bash
python scripts/sync_team_logos_to_frontend.py
```

Details: **[docs/TEAM_LOGOS.md](docs/TEAM_LOGOS.md)**.

---

## Prediction methodology (Five Keys)

The **Super Bowl / matchup engine** is built on five keys — **time of possession**, **turnovers**, **big plays**, **third-down efficiency**, and **red zone TD%** — with a **three-of-five** rule and **opponent-adjusted** weighting (SOS, defensive difficulty). A separate **QB production** lens scores postseason QB impact on drive sustainability, high-leverage downs, and off-script value, adjusted for defensive strength.

The **team model** explains tilt at the game level; the **QB engine** explains how passing-game advantage shows up on the field. Tie keys are labeled explicitly; big-play thresholds and opponent meltdown dampening are configurable in the legacy `superbowlengine` config.

---

## Tests

```bash
uv run pytest tests/ -q
```

---

## Repository history

This project grew from an explainable **Super Bowl prediction** research codebase into **GridironIQ**: the same statistical core now powers a **full web product** with draft tooling and report APIs. Older R/Shiny workflows are retired; see **[MIGRATION_R_TO_PYTHON.md](MIGRATION_R_TO_PYTHON.md)** for feature mapping.

---

## License

MIT (see `pyproject.toml`).
