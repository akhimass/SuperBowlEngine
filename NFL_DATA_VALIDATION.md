# NFL Data Validation

**nflreadpy installed**: yes (verified via `uv run` import check).

**PBP / Schedule sanity check (scripts/test_nfl_data_load.py)**
- Season tested: 2024
- PBP rows loaded: 49492
- Schedule rows loaded: 285
- Sample PBP columns present: `away_score`, `away_team`, `defteam`, `down`, `drive`, `drive_time_of_possession`, `fumble_lost`, `game_id`, `home_score`, `home_team`, `interception`, `play_type`, `posteam`, `season_type`, `touchdown`, `week`, `yardline_100`, `yards_gained`, `ydstogo`
- GB plays found: 2896
- DET plays found: 2991

**Test suite status**
- Command: `uv run pytest`
- Result: **92 passed, 1 skipped**
- Core report tests:
  - `tests/test_situational_reports.py` – passed
  - `tests/test_matchup_report.py` – passed
  - `tests/test_heatmaps.py` – passed (using matplotlib Agg backend)

**Integration test (tests/test_full_pipeline.py)**
- `test_full_pipeline_matchup_and_report` (2024, GB vs DET): **passed**
  - `run_matchup` returns non-empty `win_probability`, `projected_score`, `keys_won`
  - `generate_report` returns non-empty `summary`, `team_a_strengths`, `team_b_strengths`, `prediction_explanation`
- `test_full_pipeline_backtest` (2024 season): **passed**
  - `run_backtest` returns `BacktestResult` with `accuracy` in \\[0, 1] and non-empty `calibration_data`

**Pipeline behaviour / failure modes**
- All loaders use `nflreadpy` under the hood via `superbowlengine.data.load.get_pbp` and `get_schedules`.
- `scripts/test_nfl_data_load.py` exits with non-zero status if:
  - PBP or schedule is empty, or
  - any `REQUIRED_PBP_COLUMNS` are missing.
- `gridironiq.matchup_engine._load_pbp_and_schedules` raises `RuntimeError` if PBP or schedules are empty for the requested season.
- `gridironiq.backtest_engine.run_backtest`:
  - raises `RuntimeError` when schedules are unavailable for a season
  - returns `accuracy=0.0` and empty `calibration_data` only when there are no scored games after filtering.

**Confirmation**

**Real NFL data pipeline is working**: play-by-play and schedules for 2024 load successfully from nflreadpy/nflverse, the matchup engine and report generator run end-to-end for a real GB–DET matchup, the backtest engine runs on 2024, and the full pytest suite (including integration tests) passes.
