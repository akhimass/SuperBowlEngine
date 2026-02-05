"""
Strength of schedule (SOS): average opponent win% from game results.

Game results can be derived from PBP (build_game_results) or from schedule data.
SOS is computed from regular-season games only; filter PBP by season_type before
building or pass only REG game results. No external APIs required.
"""

from typing import Dict, Optional

import pandas as pd


def build_game_results(
    pbp: pd.DataFrame,
    *,
    season_type: Optional[str] = None,
) -> pd.DataFrame:
    """
    Build one row per game with final scores from play-by-play data.
    Uses max home_score / away_score per game_id (scores in PBP are cumulative per play).
    Returns columns: game_id, home_team, away_team, home_score_final, away_score_final.
    Optional season_type filters to that season (e.g. "REG" for regular season only).
    """
    df = pbp.copy()
    if season_type is not None and "season_type" in df.columns:
        df = df[df["season_type"] == season_type]
    if df.empty:
        return pd.DataFrame(
            columns=["game_id", "home_team", "away_team", "home_score_final", "away_score_final"]
        )
    agg = df.groupby("game_id").agg(
        home_team=("home_team", "first"),
        away_team=("away_team", "first"),
        home_score_final=("home_score", "max"),
        away_score_final=("away_score", "max"),
    ).reset_index()
    return agg


def compute_team_win_pct(game_results: pd.DataFrame) -> pd.Series:
    """
    Compute each team's win percentage from game results.
    game_results must have: home_team, away_team, home_score_final, away_score_final.
    Returns a Series indexed by team with values in [0, 1].
    """
    g = game_results.copy()
    g["home_win"] = (g["home_score_final"] > g["away_score_final"]).astype(int)
    g["away_win"] = (g["away_score_final"] > g["home_score_final"]).astype(int)
    home_wins = g.groupby("home_team")["home_win"].sum()
    away_wins = g.groupby("away_team")["away_win"].sum()
    wins = home_wins.add(away_wins, fill_value=0)
    home_gp = g["home_team"].value_counts()
    away_gp = g["away_team"].value_counts()
    gp = home_gp.add(away_gp, fill_value=0)
    return (wins / gp).fillna(0.0)


def compute_sos(game_results: pd.DataFrame, team: str) -> float:
    """
    Strength of schedule: average opponent win% for the given team's games.
    Use game_results from regular season only (e.g. build_game_results(pbp, season_type="REG")).
    Returns 0.0 if the team has no games.
    """
    win_pct = compute_team_win_pct(game_results)
    g = game_results
    opps_home = g.loc[g["home_team"] == team, "away_team"]
    opps_away = g.loc[g["away_team"] == team, "home_team"]
    opps = pd.concat([opps_home, opps_away], ignore_index=True)
    if len(opps) == 0:
        return 0.0
    return float(win_pct.reindex(opps).mean())


def zscore_sos(all_team_sos: Dict[str, float]) -> Dict[str, float]:
    """
    Convert SOS values to z-scores (mean 0, std 1) across teams.
    If there are 0 or 1 teams, returns the same values (no division by zero).
    """
    if not all_team_sos:
        return {}
    vals = list(all_team_sos.values())
    n = len(vals)
    mean = sum(vals) / n
    if n < 2:
        return {t: 0.0 for t in all_team_sos}
    variance = sum((x - mean) ** 2 for x in vals) / (n - 1)
    std = variance ** 0.5
    if std == 0:
        return {t: 0.0 for t in all_team_sos}
    return {t: (sos - mean) / std for t, sos in all_team_sos.items()}


def compute_team_sos(season_games: pd.DataFrame, team: str) -> float:
    """
    Backward-compatible SOS: average opponent win%.
    season_games must have: game_id, home_team, away_team, and either
    (home_score_final, away_score_final) or (home_score, away_score).
    """
    g = season_games.copy()
    if "home_score_final" in g.columns and "away_score_final" in g.columns:
        h, a = g["home_score_final"], g["away_score_final"]
    else:
        h, a = g["home_score"], g["away_score"]
    g = g.assign(home_score_final=h, away_score_final=a)
    return compute_sos(g, team)
