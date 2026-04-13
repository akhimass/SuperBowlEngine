# GridironIQ draft engine

## How team-specific calibration works

All team-specific behavior is **computed at runtime** from nflverse and (optionally) CFBD data. **No manual need priors exist in this codebase.** Every need score is derived from the loaders in `loaders.py` (`load_pbp_reg`, `load_snap_counts`, `load_injuries`, `load_player_stats_reg`) and CFBD HTTP APIs where enabled.

### Five need signals

1. **PBP EPA** — Regular-season play-by-play: pass/rush offense and defense EPA, z-scored vs the league, mapped into position buckets (`team_needs.py`, `EPA_NEED_MAP`).
2. **Snap depth** — Snap-count concentration among top players per bucket (thin rooms score higher need).
3. **Injuries** — Severe roster statuses (out / IR / doubtful) add pressure by position bucket.
4. **Room production (z-based)** — `player_stats` season totals for TE, WR, and EDGE (DE+OLB) vs league z-scores; weak rooms increase need (`room_production.py`).
5. **Share trends** — Linear slope over the last three seasons of TE/WR/RB target shares (skill group) and EDGE sack+QB-hit totals vs league mean (`compute_position_share_trend`, used in `team_context.py`). Slopes feed scheme-fit bonuses for EDGE and appear in `team_context_summary`.

Normalized **combined** need scores (0–100) are the max-rescaled sum of the raw EPA, snap, injury, and room contributions. **Per-layer** normalized views are exposed on `compute_team_needs(...)[\"signal_layers\"]` and on `TeamContext`.

### Scheme fit (by position bucket)

- **Base**: Cosine alignment between a **10-D team vector** (7 PBP tendencies + 3 pass-game shares from `player_stats`) and a **player archetype vector** (`scheme_fit.py`). nflverse PBP in this build does **not** expose an offensive `personnel` column; `raw[\"personnel_proxy_note\"]` documents the substitute (WR/TE/RB target and air-yards shares).
- **TE**: `infer_te_archetype` (size/speed + optional explicit tag) and `te_share_fit_score` scale fit so high team TE usage favors receiving profiles and low usage favors inline/Y profiles.
- **EDGE**: `edge_pressure_trend_fit_bonus` from `TeamContext.edge_pressure_trend` (declining pass-rush proxy → small fit bump).
- **OT / IOL**: `ot_pass_rate_fit_bonus` from team pass rate.
- **WR**: `wr_scheme_signals` surfaces WR target share, WR air-yards share, and a simple boundary-usage proxy (no fabricated charting data).

Pass a **`TeamContext`** into `compute_scheme_fit(..., team_context=ctx)` so the pipeline does not rebuild profiles mid-run (`pipeline.py`).

### CFBD competition weighting

Conference names come from CFBD **`/teams`** for the stats season (`cfb_client.fetch_cfbd_team_conferences`). `CONFERENCE_COMPETITION_WEIGHT` in `cfb_stats.py` scales raw efficiency-style inputs **before** within-class percentiling for:

- TE usage efficiency (`cfb_te_usage_efficiency_score`, with `cfb_te_usage_efficiency_score_raw` and `cfb_te_usage_efficiency_adjusted_value` stored for audit),
- WR efficiency in the production/efficiency percentile pass,
- EDGE pressure proxy percentiles.

Each matched prospect row includes `cfb_conference` and `cfb_competition_weight` when available.

### Running the pipeline for any team

From the repo root (with the package installed, e.g. `uv run`):

```bash
python -m gridironiq.draft.pipeline --team KC --season 2025 --picks 23 54 87 --top-n 10
```

- **`--team`**: required NFL abbreviation.
- **`--season`**: eval season (PBP / stats year).
- **`--combine-season`**: optional; defaults to `season + 1` for the rookie class.
- **`--picks`**: optional list of owned draft slots (metadata in `TeamContext` / summary).
- **`--top-n`**: number of prospects printed.

Programmatic use: `build_draft_board(team, combine_season, eval_season, draft_pick_positions=[...])` returns `team_context_summary`, full `team_needs`, and graded prospects.

### Auditing `need_signal_policy`

`need_signal_policy` (on `compute_team_needs` and `TeamContext`) includes:

- `manual_need_priors`: always `False`.
- `sources`: concrete data channels used.
- `team`, `season`, and (from context) `trend_window_seasons`.

Use `signal_layers` on the `compute_team_needs` payload to see EPA-only, snap-only, injury-only, and room-only normalized views.

### Runtime context object

`build_team_context(team, season, draft_pick_positions=...)` returns a **`TeamContext`** dataclass: single place for needs, scheme vector, room/snap/injury layers, trends, and policy. `repr(context)` prints a ranked need summary for debugging any team.
