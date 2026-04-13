# GridironIQ — Web UI

Vite + React + TypeScript frontend for **GridironIQ**: matchup engine, schedule, draft room, **2026 Round 1 mock draft** (`/draft/simulator`), reports, and backtesting views. Calls the Python **FastAPI** backend via `VITE_API_BASE_URL`.

## Local development

```bash
npm install
npm run dev
```

Default API target is `http://127.0.0.1:8000` (see `src/lib/api.ts`). Override with:

```bash
# .env.local (not committed)
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Production build

```bash
npm run build
npm run preview   # optional: test dist/ locally
```

## Deploy on Vercel

1. **New Project** → import this Git repo.
2. Set **Root Directory** to `gridiron-intel` (monorepo).
3. Framework preset can stay **Other**; `vercel.json` sets `buildCommand` and `outputDirectory`.
4. **Environment variables** (Production + Preview):
   - `VITE_API_BASE_URL` = your public FastAPI URL, e.g. `https://your-api.onrender.com` (no trailing slash).

Vercel preview URLs (`*.vercel.app`) are allowed by the API CORS regex by default. For a **custom domain**, set on the API host:

```bash
GRIDIRONIQ_CORS_ORIGINS=https://your-app.vercel.app,https://www.yourdomain.com
```

Optional: override or disable the Vercel regex with `GRIDIRONIQ_CORS_ORIGIN_REGEX` (empty string disables the regex; set explicit origins only).

The **mock draft simulator** and static assets under `public/` work without the API. **Draft Room**, **Matchup**, and other tabs need the backend running and CORS configured.
