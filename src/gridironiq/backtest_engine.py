from dataclasses import dataclass, asdict
from typing import Any, Dict, List

import pandas as pd

from superbowlengine.data import SeasonNotAvailableError, get_schedules

from .matchup_engine import run_matchup


@dataclass
class BacktestRun:
  """Single game backtest record."""

  season: int
  week: str
  home_team: str
  away_team: str
  predicted_win_prob: float  # for home team
  predicted_score_home: int
  predicted_score_away: int
  actual_score_home: int
  actual_score_away: int
  correct: bool

  def to_dict(self) -> Dict[str, Any]:
      return asdict(self)


@dataclass
class BacktestResult:
    accuracy: float
    average_score_error: float
    calibration_data: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def run_backtest(season: int) -> BacktestResult:
    """
    Run backtest for a single season.

    For each game with final scores:
      - treat home team as team_a in the matchup engine
      - run prediction
      - compare predicted winner vs actual winner
      - compute score error
    """
    try:
        schedules = get_schedules([season])
    except SeasonNotAvailableError as e:
        raise RuntimeError(f"Schedules not available for season {season}: {e}") from e

    if schedules.empty:
        return BacktestResult(accuracy=0.0, average_score_error=0.0, calibration_data=[])

    if "season" in schedules.columns:
        schedules = schedules[schedules["season"].astype(str) == str(season)]

    # Only consider games with final scores
    mask_scores = (
        schedules["home_score"].notna()
        & schedules["away_score"].notna()
    )
    # nflreadpy schedules expose game_type instead of season_type; alias it.
    if "season_type" not in schedules.columns and "game_type" in schedules.columns:
        schedules = schedules.rename(columns={"game_type": "season_type"})

    games = schedules.loc[mask_scores, ["game_id", "week", "season_type", "home_team", "away_team", "home_score", "away_score"]].copy()
    if games.empty:
        return BacktestResult(accuracy=0.0, average_score_error=0.0, calibration_data=[])

    runs: List[BacktestRun] = []
    total_correct = 0
    total_score_error = 0.0

    for _, row in games.iterrows():
        home = str(row["home_team"])
        away = str(row["away_team"])
        week_label = str(row.get("week", "")) or str(row.get("game_id", ""))
        season_type = str(row.get("season_type", "REG")).upper()
        actual_home = int(row["home_score"])
        actual_away = int(row["away_score"])

        mode = "regular" if season_type == "REG" else "opp_weighted"

        try:
            matchup = run_matchup(season=season, team_a=home, team_b=away, mode=mode)
        except Exception:
            # Skip games where data is missing or prediction fails
            continue

        prob_home = float(matchup.win_probability)
        predicted_scores = matchup.projected_score or {}
        pred_home = int(predicted_scores.get(home, 0))
        pred_away = int(predicted_scores.get(away, 0))

        predicted_winner = matchup.predicted_winner or (home if prob_home >= 0.5 else away)
        actual_winner = home if actual_home > actual_away else away
        correct = predicted_winner == actual_winner

        score_error = abs(pred_home - actual_home) + abs(pred_away - actual_away)

        total_score_error += score_error
        if correct:
            total_correct += 1

        runs.append(
            BacktestRun(
                season=season,
                week=week_label,
                home_team=home,
                away_team=away,
                predicted_win_prob=prob_home,
                predicted_score_home=pred_home,
                predicted_score_away=pred_away,
                actual_score_home=actual_home,
                actual_score_away=actual_away,
                correct=correct,
            )
        )

    n = len(runs)
    if n == 0:
        return BacktestResult(accuracy=0.0, average_score_error=0.0, calibration_data=[])

    accuracy = total_correct / n
    # average per-team absolute error in points
    average_score_error = (total_score_error / (2 * n)) if n > 0 else 0.0

    calibration_data = [r.to_dict() for r in runs]
    return BacktestResult(
        accuracy=round(accuracy, 4),
        average_score_error=round(average_score_error, 2),
        calibration_data=calibration_data,
    )


