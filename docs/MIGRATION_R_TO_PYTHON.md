# Migration: NFL_Report_Engine (R) → GridironIQ (Python)

This document describes how the former R scouting report engine mapped into the Python-powered GridironIQ platform, and which concepts and outputs are now implemented in Python. The original R project directory (`NFL_Report_Engine/`) has been removed from the repo; all reporting functionality is now Python-native.

---

## Section 1: What the R Engine Did

Historically, the R Shiny app in `NFL_Report_Engine/app.R` provided the following functional outputs and workflows:

| Output / Workflow | Description |
|-------------------|-------------|
| **Matchup reports** | Team-vs-team matchup selection (Team 1 vs Team 2); drives all downstream visuals. |
| **Run tendency heatmap** | Run % by down/distance × field position; cell labels show run/pass success (S/T). Color = run tendency. |
| **Pass tendency heatmap** | Pass % by down/distance × field position; same layout as run heatmap. |
| **Success rank heatmap** | Team’s offensive success rate rank vs. NFL (1–32) by situation; run rank, pass rank, avg rank per cell. |
| **Run direction map** | Bar chart: left/middle/right run frequency and efficiency (YPC, EPA/run). |
| **QB passing heatmap** | Completion % by pass location (left/middle/right) × depth (behind LOS, short, intermediate, deep); head-to-head matchup weeks. |
| **Detailed matchup table** | Offense vs defense by situation × play type (Pass: Shotgun/Under Center, Run: Left/Middle/Right). Shows plays, EPA/play, yards/play, success rank for offense and defense. Rendered as `gt` table. |
| **Broadcast-style report** | (Referenced in output PNGs e.g. `*_Broadcast_Report.png`.) Short, media-friendly summary and talking points. |
| **Presentation report** | (Referenced in `*_Presentation_Report.png`.) Slide-friendly bullets and key edges. |
| **Offseason moves** | Table of key additions/losses (incoming, retired, FA/trade) from `NFL_Offseason_Moves.xlsx`. |
| **Draft report** | 2025 draft class per team from `NFL_2025_Draft_Results.xlsx`. |

Selected legacy output assets (e.g. matchup PNGs, broadcast/presentation reports, heatmaps, and detailed matchup tables) have been copied into `outputs/legacy_reports/` and `gridiron-intel/public/reports/` as static examples.

---

## Section 2: Data Dependencies

### PBP columns used (from former `prepare_data.R` and `app.R`)

- **Core:** `season_type`, `posteam`, `defteam`, `week`, `play_type`, `down`, `ydstogo`, `yardline_100`, `pass_attempt`, `rush_attempt`, `qb_scramble`, `passer_player_name`, `rusher_player_name`, `receiver_player_name`, `pass_location`, `air_yards`, `yards_gained`, `complete_pass`, `success`, `epa`, `shotgun`, `run_location`, `pass_touchdown`, `rush_touchdown`

### Transformations in the former R engine

- Data prep script (`prepare_data.R`) loaded full-season PBP via `nflfastR::load_pbp(2024)` and trimmed to the columns above.
- The Shiny app (`app.R`) then:

- Filters to `season_type == 'REG'`, non-NA `down`, and plays with `pass_attempt | rush_attempt | qb_scramble`, excludes `play_type == "no_play"`.
- Adds `play_category`: "Pass" if pass or scramble, else "Run".
- **Distance buckets (`dist_bucket`):**  
  - 1st: `ydstogo >= 10` → "1st & 10+", else "1st & <10"  
  - 2nd: ydstogo 7+, 3–6, 1–2 → Long / Medium / Short  
  - 3rd / 4th: same bands → Long / Medium / Short  
  - Else "Other"; filtered out.
- **Field position buckets (`field_pos_bucket`):**  
  - `yardline_100 >= 91` → "Backed Up (Own 1-9)"  
  - 21–90 → "In the Field (Own 10-Opp 21)"  
  - 11–20 → "Upper Red Zone (Opp 20-11)"  
  - 3–10 → "Lower Red Zone (Opp 10-3)"  
  - 1–2 → "Goal Line (Opp 2-1)"  
  - Else "Other"; filtered out.
- Heatmaps and tables are built from `pbp_final` (bucketed, non-Other only).

### How outputs were assembled

- **Heatmaps:** `ggplot2` tile plots; x = field position, y = down/distance; fill = run %, pass %, or rank; labels in cells.
- **Matchup table:** `gt` table from joined offense summary (posteam, situation, breakdown) and defense summary (defteam, situation, breakdown); optional team logos/colors from `teams_colors_logos`.
- **QB passing heatmap:** Filter to QB’s pass plays in matchup weeks; bucket by `pass_location` and `air_yards` depth; completion % by zone.
- **Run direction:** Group by `run_location` (left/middle/right); sum runs, mean EPA, mean yards.
- **Offseason/Draft:** Read from Excel; filter by team nickname/abbreviation.

---

## Section 3: Mapping to Python

| R feature | Current R file/function | Planned Python module | Status |
|-----------|--------------------------|------------------------|--------|
| Situational buckets (down/distance, field pos) | app.R (mutate dist_bucket, field_pos_bucket) | `reports/situational.py` | done |
| Run/pass tendency by situation | app.R (generate_run_tendency_heatmap, generate_pass_tendency_heatmap) | `reports/situational.py` + `reports/heatmaps.py` | done |
| Success rate by situation | app.R (summarise success) | `reports/situational.py` | done |
| Success rank heatmap | app.R (generate_rank_heatmap) | `reports/heatmaps.py` | done |
| Run direction map | app.R (generate_run_direction_map) | `reports/situational.py` + `reports/heatmaps.py` | done |
| QB passing heatmap (location × depth) | app.R (generate_passing_heatmap) | `reports/heatmaps.py` | done |
| Offense vs defense detailed table | app.R (generate_detailed_matchup_table) | `reports/matchup_report.py` + situational | done |
| Matchup report summary | app.R (full report_data list) | `reports/matchup_report.py` + `report_generator.py` | partial / done |
| Broadcast-style report | app.R + PNG exports | `reports/broadcast_report.py` | done |
| Presentation-style report | app.R + PNG exports | `reports/presentation_report.py` | done |
| Output paths / asset naming | R writes ad hoc | `reports/report_assets.py` | done |
| Offseason moves (Excel) | app.R (generate_moves_list) | Optional / legacy or separate data | pending |
| Draft class (Excel) | app.R (generate_draft_report) | Optional / legacy or separate data | pending |

---

## Section 4: What Already Exists in Python

- **`src/superbowlengine/features`:** Keys (TOP, TO, big plays, 3rd down, red zone), SOS, opponent weights, per-game keys, keys pipeline. Used for win probability and score projection; **not** situational down/distance/field-position bucketing.
- **`src/superbowlengine/models`:** Professor Keys predictor, score model, turnover regression. Drives predicted winner, win prob, projected score.
- **`src/superbowlengine/qb`:** QB production (drive sustain, situational, off-script), defense-adjusted; box-score and PBP-based. Complements but does not replace R’s QB *passing heatmap* (location/depth).
- **`src/gridironiq/matchup_engine.py`:** Runs matchup (keys + predict + score); returns `MatchupResult`. Used by report generators.
- **`src/gridironiq/report_generator.py`:** `generate_report(matchup_result)` returns structured scouting JSON (summary, team strengths, offensive/defensive profile, prediction explanation, confidence notes). Covers high-level narrative, not situational heatmaps or offense-vs-defense tables.

So: **team-level prediction, score, and narrative report** are already in Python. **Situational bucketing, tendency heatmaps, success ranks, offense-vs-defense breakdowns, broadcast/presentation narratives, and asset naming** are added in `src/gridironiq/reports/`.

---

## Section 5: Migration Priority

1. **High (value + reuse):** Situational buckets and run/pass tendency by situation → used by heatmaps, matchup report, and broadcast/presentation. **Done in `reports/situational.py`.**
2. **High:** Run/pass and success-rank heatmaps → core to “Team Report” and matchup views. **Done in `reports/heatmaps.py`.**
3. **High:** Matchup report combining engine output + situational edges + offense-vs-defense. **Done in `reports/matchup_report.py`.**
4. **Medium:** Broadcast and presentation reports (short copy + talking points). **Done in `reports/broadcast_report.py` and `reports/presentation_report.py`.**
5. **Medium:** QB passing heatmap (location × depth). **Done in `reports/heatmaps.py`.**
6. **Lower (external data):** Offseason moves and draft class depend on Excel files; can remain R-only or be ported later with a separate data pipeline.

---

## R Features Fully Ported vs Pending

- **Fully ported (Python-native):** Situational bucketing; run/pass tendency by situation; success rate by situation; run/pass heatmap; success rank heatmap; run direction summary; offense-vs-defense situational comparison; matchup report JSON; broadcast report JSON; presentation report JSON; report asset paths and naming; QB passing heatmap (location × depth).
- **Pending / optional:** Offseason moves table (Excel); draft class table (Excel). These can be added later or left to the R app for now.

---

## R Engine Removal

All major reporting capabilities of the former R engine (situational bucketing, tendencies, heatmaps, matchup tables, and broadcast/presentation views) have been ported into Python modules under `src/gridironiq/reports/`. The `NFL_Report_Engine/` directory and any R bridge code have been removed from the repository, and there is no runtime dependency on R. A small set of example PNG outputs has been preserved under `outputs/legacy_reports/` and `gridiron-intel/public/reports/` purely as design and portfolio references.
