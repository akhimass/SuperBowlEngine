# GridironIQ / RMU SAC — Full context pack for a new presentation (give this to Claude)

Use this document as the **single source of truth** when redesigning the deck. It consolidates **what the system does**, **where outputs live**, **how to regenerate everything**, **metrics**, **data provenance**, and **judge-facing framing**. Attach or paste the referenced files if Claude’s context window allows.

---

## 1) Copy-paste prompt for Claude (short)

```
You are designing a replacement slide deck (PowerPoint or Google Slides) for a NON-TECHNICAL judging panel. Topic: 2026 NFL Draft — first-round projections for QB, WR, and RB using the GridironIQ / RMU SAC project in repo SuperBowlEngine.

Constraints:
- Target length: ≤10 minutes spoken (~12–15 slides max).
- Audience: judges who care about sound predictions, model justification, limitations, actionable “who to target,” visuals, and a proper Works Cited.
- Tone: confident but honest; translate AUC / probabilities into plain English; avoid jargon unless you define it once.
- Must include: (1) clear predictions for 1st-round caliber QB/WR/RB, (2) model choice + why, (3) how strong/confident we can be, (4) feature importance in owner-friendly language, (5) limitations + missing data that would help, (6) explicit recommendation to a GM/owner on who to target, (7) visuals (headshots, probability badges, simple charts), (8) Works Cited with real URLs.

Source material: follow CLAUDE_PRESENTATION_CONTEXT.md in the repo root. Prefer numbers from outputs/real_predictions/metrics_summary.json and tables from *_predictions.csv / r1_board_combined.csv. Headshots and manifest: outputs/real_predictions/prospect_manifest.json + headshots/*.png (regenerate via pipeline command below).

Do NOT claim the model predicts exact pick numbers or team-specific draft order; it outputs P(R1) = probability of being drafted in round 1. The UI mock draft combines that with a full combine board and ESPN-style needs for illustration only.

Deliverable: outline + slide-by-slide content + speaker notes + image/chart placeholders + Works Cited list.
```

---

## 2) Project identity

| Field | Value |
|--------|--------|
| **Name** | GridironIQ (draft / analytics) + RMU SAC hackathon track |
| **Author** | Akhi Chappidi · UNC Charlotte |
| **Repo** | SuperBowlEngine (also pushed to GridironIQ remote) |
| **Frontend** | `gridiron-intel/` (Vite + React) — Draft Room, mock draft, engine panels |
| **Backend** | Python `src/gridironiq/` — models, nflverse loaders, CFBD client, draft pipeline, optional FastAPI |

---

## 3) Original judging rubric (map every slide to this)

1. **Predictions** — Name specific QB / WR / RB prospects the model favors for round 1; show P(R1) and confidence tier.
2. **Modeling** — Why Logistic Regression + XGBoost ensemble; what AUC means in plain English; ensemble weights **40% LR / 60% XGB** (`src/gridironiq/models/first_round_model.py`).
3. **Interpretability** — Top drivers per position (from feature importance CSVs); tie to football concepts (size, production, conference strength, postseason, etc.—see pipeline).
4. **Limitations** — No true “pick 17 to Team X”; class imbalance; combine imputation; no NFL medical/character; CFBD match risk; etc.
5. **Communication** — Suggested targets for the “owner” with reasoning tied to probabilities + needs.
6. **Execution** — ≤10 min; clean visuals; no spelling noise; Works Cited.

---

## 4) Regenerate “everything” (commands)

Run from repo root `SuperBowlEngine/` (Python 3). `CFBD_API_KEY` in `.env` for headshots + CFBD-enriched board.

```bash
# 1) Full RMU real pipeline + headshots + sync to frontend public folders
python3 scripts/run_real_draft_engine.py

# 2) Combined R1 board CSV + markdown table (P(R1) ≥ 0.50 filter for printed table)
python3 scripts/report_r1_projections.py

# 3) 2026 draft order JSON (257 picks, trades, needs) → outputs + gridiron-intel/public/data
python3 scripts/build_2026_draft_order.py

# 4) PowerPoint (existing programmatic deck — replace with Claude-designed deck using same facts)
python3 scripts/build_real_presentation.py
# Output path (from script): outputs/presentations/rmu_sac_2026_final.pptx
```

Optional: start API for live nflverse board in Draft Room (`scripts/run_backend.py` or your FastAPI entry).

---

## 5) Model outputs (paths & role)

### 5.1 RMU / SAC first-round engine (QB, WR, RB only — 42 test prospects)

| Artifact | Path (after pipeline) | Notes |
|----------|------------------------|--------|
| QB / WR / RB predictions | `outputs/real_predictions/{qb,wr,rb}_predictions.csv` | Columns include `r1_probability`, `confidence`, `r1_predicted` |
| Feature importance | `outputs/real_predictions/{qb,wr,rb}_feature_importance.csv` | For “why the model likes this player” |
| Metrics | `outputs/real_predictions/metrics_summary.json` | Holdout AUCs (below) |
| Plots | `outputs/real_predictions/plots/*.png` | ROC, confusion, feature charts |
| Headshots + manifest | `outputs/real_predictions/headshots/*.png`, `outputs/real_predictions/prospect_manifest.json` | CFBD roster → ESPN athlete id → `a.espncdn.com` headshots |
| Combined board | `outputs/real_predictions/r1_board_combined.csv` | Cross-position sort; synced to `gridiron-intel/public/engine/r1_board_combined.csv` |

**Published holdout AUC (from `metrics_summary.json` on disk):**

| Position | Logistic Regression AUC | XGBoost AUC |
|----------|-------------------------|-------------|
| QB | 0.750 | 0.801 |
| WR | 0.782 | 0.767 |
| RB | 0.718 | 0.725 |

**Ensemble:** 40% LR + 60% XGBoost blended probability, then confidence bands (LOW / MEDIUM / HIGH / LOCK) from cut points in `rmu_predictions.py`.

**Core code:** `src/gridironiq/models/first_round_model.py`, `data_pipeline.py`, `rmu_predictions.py`, `rmu_visualizations.py`.

**Training / test tables:** `TrainingData/`, `TestingData/` → normalized copies under `data/rmu_sac_real/`.

### 5.2 Broader “game engine” (not the same as R1 prospect model)

Synced to `gridiron-intel/public/engine/` for the Draft Room “ENGINE” analytics:

| Artifact | Purpose |
|----------|---------|
| `win_prob_model.json`, `margin_model.json`, `total_model.json` | Game outcome stack |
| `score_model.json` | Combined score model |
| `schedule_{2020..2025}.json` | Backtest / accuracy narrative |
| `def_strength_2025.csv` | Defensive strength context |
| `sample_prediction.json` | Example single-game prediction |

Use this only if the talk briefly positions “full platform” beyond draft.

### 5.3 Draft order + needs (mock UI, not the RMU training label)

| Artifact | Path |
|----------|------|
| Full 2026 order (257 picks, trades, comp, ESPN-style needs) | `gridiron-intel/public/data/nfl_draft_order_2026.json` (source script `scripts/build_2026_draft_order.py`) |

**Important for the deck:** RMU labels are historical “was this player a round-1 pick in our training window?” — the **mock draft** merges nflverse combine grades + ESPN needs + RMU overlay for **storytelling**, not a second supervised label.

---

## 6) Data sources (Works Cited anchors)

Use the same categories as `scripts/build_real_presentation.py` (hyperlinked appendix there). Minimum set:

1. **nflverse** (R `nflreadpy` in Python) — `load_pbp`, `load_combine`, `load_draft_picks`, rosters, snaps, injuries, player stats — for historical patterns and combine-class features in the full draft board pipeline (`src/gridironiq/draft/`).
2. **CollegeFootballData (CFBD)** — API key `CFBD_API_KEY`; roster endpoint to resolve players and bridge to ESPN headshots.
3. **ESPN CDN** — `https://a.espncdn.com/i/headshots/college-football/full/<id>.png` (ids from CFBD roster payload).
4. **RMU labeled training CSVs** — `TrainingData/` (historical), `TestingData/` (2026 holdout pool with real names).
5. **Draft order / needs for mock** — user-transcribed ESPN 2026 order in `scripts/build_2026_draft_order.py` → JSON (disclose as “published draft order snapshot” not NFL official endorsement).

---

## 7) Frontend (for screenshots / “live product” slide)

- **App:** `gridiron-intel/` — `npm install && npm run dev` or `npm run build`.
- **Static RMU assets:** `gridiron-intel/public/rmu/` (manifest, CSVs, metrics).
- **Static engine assets:** `gridiron-intel/public/engine/`.
- **Draft Room tabs:** Big board (top 200 by `prospect_score` + `RMU_BOARD` filter), **3-round mock** (100 picks when API board loads), simulator, team view, analytics.

Good slide fodder: screenshot **RMU_LANDING** table + **MOCK_DRAFT_3R** table + **RMU_BOARD** filter.

---

## 8) Talking points Claude should preserve

- **What is predicted:** `P(R1)` — probability the prospect is a **first-round** selection in the training distribution, **not** “pick 12 to the Jets.”
- **Who is in scope:** RMU deck focuses on **QB / WR / RB**; the combine board includes all positions for context.
- **Strength:** Dual model + real holdout AUC in the 0.72–0.80 band (position-dependent) — much more believable than “perfect AUC” on toy data.
- **Weaknesses:** position-limited model; no OL/DL/LB in RMU head; label is historical round slot not team fit; CFBD name match edge cases; medical/character/intangibles absent; mock merge is heuristic composite.
- **Owner recommendation:** pick 2–3 names with highest P(R1) + LOCK/HIGH + feature story; mention one “value / risk” name explicitly.

---

## 9) Files Claude should open first (priority order)

1. `outputs/real_predictions/metrics_summary.json`
2. `outputs/real_predictions/prospect_manifest.json`
3. `outputs/real_predictions/r1_board_combined.csv` (or `gridiron-intel/public/engine/r1_board_combined.csv`)
4. `outputs/real_predictions/qb_predictions.csv`, `wr_predictions.csv`, `rb_predictions.csv`
5. `outputs/real_predictions/qb_feature_importance.csv` (and WR/RB counterparts)
6. `scripts/build_real_presentation.py` — narrative flavor strings + slide structure reference
7. `scripts/run_real_draft_engine.py` — docstring pipeline story
8. `gridiron-intel/public/data/nfl_draft_order_2026.json` — only if slides mention mock / team needs

---

## 10) What *you* should attach when chatting with Claude

Minimum viable bundle:

1. This file: **`CLAUDE_PRESENTATION_CONTEXT.md`** (entire file).
2. **`metrics_summary.json`**
3. **`prospect_manifest.json`**
4. **`r1_board_combined.csv`** (or top 15 rows pasted + note “full file in repo”).
5. **One feature-importance CSV** per position (or merged excerpt).
6. **3–6 headshot PNGs** for the hero prospects you will name on camera.
7. (Optional) **One ROC or calibration PNG** from `outputs/real_predictions/plots/`.

That is enough for Claude to write a **better** deck than the auto-`python-pptx` builder, while staying faithful to your actual numbers.

---

## 11) Optional: export a flat “facts dump” for Claude

From repo root (creates a text bundle of small JSON/CSV snippets — adjust paths if `outputs/` is missing locally):

```bash
mkdir -p presentation_bundle
cp CLAUDE_PRESENTATION_CONTEXT.md presentation_bundle/
cp outputs/real_predictions/metrics_summary.json presentation_bundle/ 2>/dev/null || true
cp outputs/real_predictions/prospect_manifest.json presentation_bundle/ 2>/dev/null || true
head -80 outputs/real_predictions/r1_board_combined.csv > presentation_bundle/r1_board_top80_lines.txt 2>/dev/null || true
zip -r presentation_bundle.zip presentation_bundle
```

Upload **`presentation_bundle.zip`** to Claude + the short prompt in section 1.

---

*Generated as a handoff artifact for presentation redesign. Regenerate numbers by re-running `scripts/run_real_draft_engine.py` if the model or data change.*
