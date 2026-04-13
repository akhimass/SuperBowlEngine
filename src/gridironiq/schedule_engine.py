from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

import pandas as pd

from superbowlengine.data import SeasonNotAvailableError, get_schedules

from .matchup_engine import MatchupResult, run_matchup
from .pipeline_cache import (
  load_game_report_cached,
  load_schedule_predictions,
  save_game_report_cached,
  save_schedule_predictions,
)
from .report_generator import generate_report
from .reports.broadcast_report import build_broadcast_report
from .reports.matchup_report import build_matchup_report

Phase = Literal["all", "regular", "postseason"]


def _load_schedules(season: int) -> pd.DataFrame:
  """Load schedules for a season using the shared nflreadpy-based loader."""
  try:
    schedules = get_schedules([season])
  except SeasonNotAvailableError as e:
    raise RuntimeError(f"Schedules not available for season {season}: {e}") from e

  if schedules.empty:
    raise RuntimeError(f"Schedules empty for season {season}")

  if "season" in schedules.columns:
    schedules = schedules[schedules["season"].astype(str) == str(season)]

  # Normalise game_type / season_type naming
  if "season_type" not in schedules.columns and "game_type" in schedules.columns:
    schedules = schedules.rename(columns={"game_type": "season_type"})

  return schedules


def _phase_mask(df: pd.DataFrame, phase: Phase) -> pd.Series:
  if "season_type" not in df.columns:
    return pd.Series([True] * len(df), index=df.index)
  if phase == "all":
    return pd.Series([True] * len(df), index=df.index)
  if phase == "regular":
    return df["season_type"] == "REG"
  # postseason
  return df["season_type"] != "REG"


def run_schedule_predictions(season: int, phase: Phase = "all") -> List[Dict[str, Any]]:
  """
  Return schedule with actual scores and matchup predictions for a season/phase.

  Each game dict includes:
    - game_id, season, week, season_type/phase
    - home_team, away_team, home_score, away_score
    - predicted_winner, projected_score, win_probability, correct
  """
  schedules = _load_schedules(season)

  mask_phase = _phase_mask(schedules, phase)
  mask_scores = schedules["home_score"].notna() & schedules["away_score"].notna()
  games = schedules.loc[mask_phase & mask_scores].copy()
  if games.empty:
    return []

  out: List[Dict[str, Any]] = []

  for _, row in games.iterrows():
    home = str(row["home_team"])
    away = str(row["away_team"])
    game_id = str(row["game_id"])
    week = row.get("week")
    season_type = str(row.get("season_type", "")).upper()
    actual_home = int(row["home_score"])
    actual_away = int(row["away_score"])

    mode = "regular" if season_type == "REG" else "opp_weighted"

    try:
      matchup: MatchupResult = run_matchup(season=season, team_a=home, team_b=away, mode=mode)
      win_prob = float(matchup.win_probability)
      projected_score = matchup.projected_score or {}
      pred_home = int(projected_score.get(home, 0))
      pred_away = int(projected_score.get(away, 0))
      predicted_winner = matchup.predicted_winner or (home if win_prob >= 0.5 else away)
      actual_winner = home if actual_home > actual_away else away
      correct = predicted_winner == actual_winner
    except Exception:
      # If prediction fails for any reason, surface the game with pending prediction.
      win_prob = 0.5
      projected_score = {}
      pred_home = 0
      pred_away = 0
      predicted_winner = None
      correct = False

    out.append(
      {
        "game_id": game_id,
        "season": season,
        "week": week,
        "season_type": season_type,
        "home_team": home,
        "away_team": away,
        "home_score": actual_home,
        "away_score": actual_away,
        "predicted_winner": predicted_winner,
        "predicted_score": {home: pred_home, away: pred_away},
        "win_probability": win_prob,
        "correct": bool(predicted_winner) and correct,
      }
    )

  return out


def run_schedule_reports(season: int, phase: Phase = "all") -> Dict[str, Dict[str, Any]]:
  """
  Build full report bundles for every game in a season/phase.

  Returns dict keyed by game_id so it can be cached or inspected.
  """
  schedules = _load_schedules(season)
  mask_phase = _phase_mask(schedules, phase)
  mask_scores = schedules["home_score"].notna() & schedules["away_score"].notna()
  games = schedules.loc[mask_phase & mask_scores].copy()
  if games.empty:
    return {}

  out: Dict[str, Dict[str, Any]] = {}
  for _, row in games.iterrows():
    game_id = str(row["game_id"])
    report = build_game_report(season, game_id)
    out[game_id] = report
  return out


def list_schedule(season: int, phase: Phase = "all") -> List[Dict[str, Any]]:
  """
  Public helper used by the API: load cached predictions when available,
  otherwise compute and cache them.
  """
  cached = load_schedule_predictions(season, phase)
  if cached is not None:
    return cached
  games = run_schedule_predictions(season, phase)
  save_schedule_predictions(season, phase, games)
  return games


def build_game_report(season: int, game_id: str) -> Dict[str, Any]:
  """
  Build a full report for a single historical game.

  Combines:
    - schedule metadata
    - matchup prediction (run_matchup)
    - structured scouting report (generate_report)
    - situational + broadcast views (Python-native reports)
  """
  cached = load_game_report_cached(season, game_id)
  if cached is not None:
    return cached

  schedules = _load_schedules(season)
  row: Optional[pd.Series] = None
  try:
    row = schedules.loc[schedules["game_id"] == game_id].iloc[0]
  except Exception as e:  # noqa: BLE001
    raise RuntimeError(f"Game {game_id} not found for season {season}") from e

  home = str(row["home_team"])
  away = str(row["away_team"])
  week = row.get("week")
  season_type = str(row.get("season_type", "")).upper()
  actual_home = int(row["home_score"])
  actual_away = int(row["away_score"])

  mode = "regular" if season_type == "REG" else "opp_weighted"

  matchup = run_matchup(season=season, team_a=home, team_b=away, mode=mode)
  scouting = generate_report(matchup)
  situational = build_matchup_report(season=season, team_a=home, team_b=away, week=week, mode=mode, generate_heatmaps=False)
  broadcast = build_broadcast_report(season=season, team_a=home, team_b=away, week=week, generate_heatmaps=False)

  report = {
    "season": season,
    "game_id": game_id,
    "week": week,
    "season_type": season_type,
    "home_team": home,
    "away_team": away,
    "home_score": actual_home,
    "away_score": actual_away,
    "matchup": matchup.to_dict(),
    "scouting_report": scouting,
    "situational": {
      "situational_edges": situational.get("situational_edges", {}),
      "offense_vs_defense": situational.get("offense_vs_defense", {}),
    },
    "broadcast": broadcast,
  }
  save_game_report_cached(season, game_id, report)
  return report

